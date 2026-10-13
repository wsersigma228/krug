from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import func, select, update

from backend.models import RefreshToken


async def login(client, account):
    client.cookies.clear()
    response = await client.post("/login", json={"username": account["username"], "password": "test-password"})
    assert response.status_code == 200
    return response


def refresh_cookie(response):
    """Refresh token as delivered to the browser: only via the HttpOnly cookie."""
    token = response.cookies.get("krug_refresh")
    assert token
    return token


async def post_refresh(client, token):
    # Sent explicitly so replaying an old token works even after the jar moved on.
    return await client.post("/refresh", cookies={"krug_refresh": token})


def age_use(db, jti_value, seconds):
    return update(RefreshToken).where(RefreshToken.jti == jti_value).values(
        used_at=datetime.now(timezone.utc) - timedelta(seconds=seconds))


def jti(token):
    return jwt.decode(token, options={"verify_signature": False})["jti"]


async def family_rows(db, token):
    """All rows of the family the given refresh token belongs to."""
    family = await db.scalar(select(RefreshToken.family_id).where(RefreshToken.jti == jti(token)))
    return (await db.scalars(select(RefreshToken).where(RefreshToken.family_id == family))).all()


async def test_login_sets_http_only_cookie_and_no_body_token(client, accounts):
    response = await login(client, accounts[0])
    assert "refresh_token" not in response.json()
    assert set(response.json()) == {"access_token", "token_type"}
    assert refresh_cookie(response)
    header = response.headers["set-cookie"].lower()
    assert "krug_refresh=" in header
    assert "httponly" in header and "samesite=strict" in header and "path=/refresh" in header
    assert "max-age=604800" in header
    assert "secure" not in header  # PUBLIC_APP_URL is http in tests


async def test_cookie_refresh_rotates_without_body_token(client, accounts, db):
    await login(client, accounts[0])
    first = client.cookies.get("krug_refresh")
    response = await client.post("/refresh")
    assert response.status_code == 200
    assert set(response.json()) == {"access_token", "token_type"}
    assert "krug_refresh=" in response.headers["set-cookie"]
    second = client.cookies.get("krug_refresh")
    assert second and second != first
    assert (await client.get("/me", headers={"Authorization": f"Bearer {response.json()['access_token']}"})).status_code == 200
    rows = await family_rows(db, second)
    assert len(rows) == 2 and sum(row.used_at is not None for row in rows) == 1


async def test_refresh_rotates_cookie_and_never_returns_refresh_token_in_json(client, accounts):
    original = refresh_cookie(await login(client, accounts[0]))
    response = await post_refresh(client, original)
    assert response.status_code == 200
    assert "refresh_token" not in response.json()
    assert set(response.json()) == {"access_token", "token_type"}
    rotated = refresh_cookie(response)
    assert rotated != original
    assert (await post_refresh(client, rotated)).status_code == 200


async def test_body_token_is_ignored(client, accounts):
    token = refresh_cookie(await login(client, accounts[0]))
    client.cookies.clear()
    # Body mode is gone: a refresh token in JSON is neither accepted nor echoed back.
    response = await client.post("/refresh", json={"refresh_token": token})
    assert response.status_code == 401
    assert "set-cookie" not in response.headers


async def test_missing_token_is_401(client):
    client.cookies.clear()
    assert (await client.post("/refresh")).status_code == 401
    assert (await client.post("/refresh", json={})).status_code == 401


async def test_reuse_after_grace_revokes_family(client, accounts, db):
    first = refresh_cookie(await login(client, accounts[0]))
    client.cookies.clear()
    rotated = refresh_cookie(await post_refresh(client, first))
    await db.execute(age_use(db, jti(first), 120))
    await db.commit()

    reuse = await post_refresh(client, first)
    assert reuse.status_code == 401
    assert await family_rows(db, first) == []
    assert (await post_refresh(client, rotated)).status_code == 401


async def test_reuse_within_grace_returns_access_only(client, accounts, db):
    token = refresh_cookie(await login(client, accounts[0]))
    client.cookies.clear()
    assert (await post_refresh(client, token)).status_code == 200
    response = await post_refresh(client, token)
    assert response.status_code == 200
    assert set(response.json()) == {"access_token", "token_type"}
    assert "set-cookie" not in response.headers
    assert len(await family_rows(db, token)) == 2


async def test_reuse_detection_ends_all_sessions(client, accounts, db):
    other_response = await login(client, accounts[0])
    other, other_access = refresh_cookie(other_response), other_response.json()["access_token"]
    victim_response = await login(client, accounts[0])
    victim = refresh_cookie(victim_response)
    client.cookies.clear()
    await post_refresh(client, victim)
    await db.execute(age_use(db, jti(victim), 120))
    await db.commit()
    assert (await post_refresh(client, victim)).status_code == 401
    assert (await post_refresh(client, other)).status_code == 401
    assert (await client.get("/me", headers={"Authorization": f"Bearer {other_access}"})).status_code == 401


async def test_cookie_refresh_twice_past_grace(client, accounts, db):
    await login(client, accounts[0])
    for _ in range(2):
        used = jti(client.cookies.get("krug_refresh"))
        assert (await client.post("/refresh")).status_code == 200
        await db.execute(age_use(db, used, 120))
        await db.commit()


async def test_password_reset_revokes_refresh_rows(client, accounts, db):
    from backend.account_tokens import decrypt_secret, issue_token
    from backend.models import AccountToken, User
    await login(client, accounts[0])
    user = await db.get(User, accounts[0]["id"])
    await issue_token(db, user, "reset")
    row = await db.scalar(select(AccountToken).where(AccountToken.user_id == user.id, AccountToken.purpose == "reset", AccountToken.consumed.is_(False)))
    token = decrypt_secret(row.encrypted_secret)
    await db.commit()
    response = await client.post("/auth/password-reset/confirm", json={"token": token, "password": "another-password"})
    assert response.status_code == 204
    assert await db.scalar(select(func.count()).select_from(RefreshToken).where(RefreshToken.user_id == user.id)) == 0


async def test_cookie_secure_when_public_url_is_https(client, accounts, monkeypatch):
    monkeypatch.setattr("backend.routes.users.PUBLIC_APP_URL", "https://krug.example")
    response = await login(client, accounts[0])
    assert "secure" in response.headers["set-cookie"].lower()


async def test_purge_expired_refresh_tokens(client, accounts, db):
    from backend.tasks.auth_tasks import purge_expired
    stale = refresh_cookie(await login(client, accounts[0]))
    live = refresh_cookie(await login(client, accounts[0]))
    await db.execute(update(RefreshToken).where(RefreshToken.jti == jti(stale)).values(
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
    assert await purge_expired(db) >= 1
    assert await db.get(RefreshToken, jti(stale)) is None
    assert await db.get(RefreshToken, jti(live)) is not None


async def test_logout_revokes_tokens_and_clears_cookie(client, accounts, db):
    await login(client, accounts[0])
    access = (await client.post("/refresh")).json()["access_token"]
    response = await client.post("/logout", headers={"Authorization": f"Bearer {access}"})
    assert response.status_code == 204
    assert 'krug_refresh=""' in response.headers["set-cookie"] or "krug_refresh=;" in response.headers["set-cookie"]
    assert "path=/refresh" in response.headers["set-cookie"].lower()
    assert await db.scalar(select(func.count()).select_from(RefreshToken).where(RefreshToken.user_id == accounts[0]["id"])) == 0


async def test_login_deletes_expired_rows(client, accounts, db):
    stale = refresh_cookie(await login(client, accounts[0]))
    await db.execute(update(RefreshToken).where(RefreshToken.jti == jti(stale)).values(
        expires_at=datetime.now(timezone.utc) - timedelta(days=1)))
    await db.commit()
    await login(client, accounts[0])
    assert await family_rows(db, stale) == []
