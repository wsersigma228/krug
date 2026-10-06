from sqlalchemy import select

from scripts import bootstrap_krug
from backend.models import User
from backend.security import create_access_token, create_refresh_token


async def test_bootstrap_preserves_ids_and_invalidates_old_tokens(db, client, monkeypatch):
    old = User(username="before_reset", hashed_password="unused", token_version=0, language="en")
    db.add(old)
    await db.flush()
    old_id = old.id
    claims = {"user_id": old.id, "version": old.token_version}
    access_token = create_access_token(claims)
    refresh_token = create_refresh_token(claims)

    # The fixture's session is bound to test_db's rollback transaction; no test can truncate persistent data.
    monkeypatch.setattr(bootstrap_krug, "DATABASE_URL", "postgresql+psycopg://test@localhost/app_test")
    monkeypatch.setattr(bootstrap_krug, "SessionLocal", lambda: db)
    monkeypatch.setattr(bootstrap_krug, "get_password_hash", lambda _password: "test-hash")
    await bootstrap_krug.bootstrap("app_test", True, {
        "username": "krugdev", "display_name": "wser220", "password": "test-password-over-20",
    })

    db.expire_all()
    new = await db.scalar(select(User).where(User.username == "krugdev"))
    assert new and new.id > old_id
    assert (await client.get("/me", headers={"Authorization": f"Bearer {access_token}"})).status_code == 401
    assert (await client.post("/refresh", json={"refresh_token": refresh_token})).status_code == 401
