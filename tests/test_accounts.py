from datetime import datetime, timedelta, timezone
from hashlib import sha256
from unittest.mock import Mock

import pytest
from sqlalchemy import select

from backend.account_tokens import decrypt_secret
from backend.models import AccountToken, EmailDelivery, User
from backend.tasks.celery_app import celery_app


async def issue_token(client, db, account, purpose):
    if purpose == "verify":
        response = await client.post("/auth/email-verification/request", headers=account["headers"])
    else:
        response = await client.post("/auth/password-reset/request", json={"email": account["email"]})
    assert response.status_code == 202, response.text
    row = await db.scalar(select(AccountToken).where(
        AccountToken.user_id == account["id"], AccountToken.purpose == purpose,
        AccountToken.consumed.is_(False),
    ).order_by(AccountToken.expires_at.desc()))
    assert row is not None
    raw = decrypt_secret(row.encrypted_secret)
    assert sha256(raw.encode()).hexdigest() == row.token_hash
    assert raw not in response.text
    return row, raw


async def test_email_confirmation_is_single_use_and_does_not_revoke_session(client, accounts, db):
    account, _ = accounts
    assert (await client.get("/me", headers=account["headers"])).json()["email_verified"] is False
    row, token = await issue_token(client, db, account, "verify")
    response = await client.post("/auth/email-verification/confirm", json={"token": token})
    assert response.status_code == 204, response.text
    me = await client.get("/me", headers=account["headers"])
    assert me.status_code == 200
    assert me.json()["email_verified"] is True
    await db.refresh(row)
    assert row.consumed is True
    assert row.encrypted_secret is None
    assert (await client.post("/auth/email-verification/confirm", json={"token": token})).status_code == 400


async def test_password_reset_changes_password_and_revokes_all_sessions(client, accounts, db):
    account, _ = accounts
    second = (await client.post("/login", json={
        "username": account["username"], "password": "test-password",
    })).json()
    row, token = await issue_token(client, db, account, "reset")
    assert (await client.post("/auth/password-reset/confirm", json={
        "token": token, "password": "replacement-password",
    })).status_code == 204
    await db.refresh(row)
    assert row.consumed is True
    assert row.encrypted_secret is None
    for tokens in [account["tokens"], second]:
        assert (await client.get("/me", headers={
            "Authorization": f"Bearer {tokens['access_token']}",
        })).status_code == 401
        assert (await client.post("/refresh", json={"refresh_token": tokens["refresh_token"]})).status_code == 401
    assert (await client.post("/login", json={
        "username": account["username"], "password": "test-password",
    })).status_code == 401
    login = await client.post("/login", json={
        "username": account["username"], "password": "replacement-password",
    })
    assert login.status_code == 200
    assert (await client.get("/me", headers={
        "Authorization": f"Bearer {login.json()['access_token']}",
    })).status_code == 200
    assert (await client.post("/auth/password-reset/confirm", json={
        "token": token, "password": "another-password",
    })).status_code == 400


@pytest.mark.parametrize("purpose", ["verify", "reset"])
async def test_expired_account_tokens_are_rejected(client, accounts, db, purpose):
    account, _ = accounts
    row, token = await issue_token(client, db, account, purpose)
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()
    endpoint = "email-verification" if purpose == "verify" else "password-reset"
    payload = {"token": token, **({"password": "replacement-password"} if purpose == "reset" else {})}
    assert (await client.post(f"/auth/{endpoint}/confirm", json=payload)).status_code == 400
    assert (await client.get("/me", headers=account["headers"])).status_code == 200
    user = await db.get(User, account["id"])
    assert user.email_verified is False
    assert user.token_version == 0


async def test_tokens_cannot_be_used_for_another_purpose(client, accounts, db):
    account, _ = accounts
    _, verify = await issue_token(client, db, account, "verify")
    _, reset = await issue_token(client, db, account, "reset")
    assert (await client.post("/auth/email-verification/confirm", json={"token": reset})).status_code == 400
    assert (await client.post("/auth/password-reset/confirm", json={
        "token": verify, "password": "replacement-password",
    })).status_code == 400


async def test_reset_request_does_not_disclose_account_existence(client, accounts, db):
    account, _ = accounts
    known = await client.post("/auth/password-reset/request", json={"email": account["email"]})
    unknown = await client.post("/auth/password-reset/request", json={"email": "not-registered@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.content == unknown.content
    tokens = (await db.scalars(select(AccountToken).where(AccountToken.purpose == "reset"))).all()
    assert len(tokens) == 1
    assert tokens[0].user_id == account["id"]


@pytest.mark.parametrize("purpose", ["verify", "reset"])
async def test_reissue_cancels_old_token_and_durable_delivery(client, accounts, db, monkeypatch, purpose):
    account, _ = accounts
    send = Mock(side_effect=ConnectionError("Broker unavailable"))
    monkeypatch.setattr(celery_app, "send_task", send)
    first, first_token = await issue_token(client, db, account, purpose)
    second, second_token = await issue_token(client, db, account, purpose)
    assert second.token_hash != first.token_hash
    await db.refresh(first)
    assert first.consumed is True
    assert first.encrypted_secret is None
    deliveries = (await db.scalars(select(EmailDelivery).where(
        EmailDelivery.token_id.in_([first.token_hash, second.token_hash]),
    ))).all()
    assert {delivery.token_id: delivery.status for delivery in deliveries} == {
        first.token_hash: "cancelled", second.token_hash: "pending",
    }
    assert all(delivery.kind == purpose and delivery.recipient_id == account["id"] for delivery in deliveries)
    assert all(delivery.post_id is None for delivery in deliveries)
    endpoint = "email-verification" if purpose == "verify" else "password-reset"
    payload = {"token": first_token, **({"password": "replacement-password"} if purpose == "reset" else {})}
    assert (await client.post(f"/auth/{endpoint}/confirm", json=payload)).status_code == 400
    send.assert_not_called()


async def test_logout_revokes_all_sessions_but_allows_new_login(client, accounts):
    account, _ = accounts
    second = (await client.post("/login", json={
        "username": account["username"], "password": "test-password",
    })).json()
    assert (await client.post("/logout", headers=account["headers"])).status_code == 204
    for tokens in [account["tokens"], second]:
        assert (await client.get("/me", headers={
            "Authorization": f"Bearer {tokens['access_token']}",
        })).status_code == 401
        assert (await client.post("/refresh", json={"refresh_token": tokens["refresh_token"]})).status_code == 401
    assert (await client.post("/logout", headers=account["headers"])).status_code == 401
    assert (await client.post("/login", json={
        "username": account["username"], "password": "test-password",
    })).status_code == 200


async def test_accounts_without_email_still_work(client):
    from uuid import uuid4
    username = f"noemail_{uuid4().hex[:10]}"
    created = await client.post("/users", json={"username": username, "password": "test-password"})
    assert created.status_code == 201
    tokens = (await client.post("/login", json={"username": username, "password": "test-password"})).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = await client.get("/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] is None
    assert me.json()["email_verified"] is False
    assert (await client.post("/auth/email-verification/request", headers=headers)).status_code == 400
    assert (await client.post("/refresh", json={"refresh_token": tokens["refresh_token"]})).status_code == 200


@pytest.mark.parametrize("endpoint,payload", [
    ("/auth/password-reset/request", {"email": "invalid"}),
    ("/auth/password-reset/request", {"email": "x@example.com\nBcc: victim@example.com"}),
    ("/auth/password-reset/request", {"email": None}),
    ("/auth/email-verification/confirm", {"token": ""}),
    ("/auth/email-verification/confirm", {"token": None}),
    ("/auth/password-reset/confirm", {"token": "opaque", "password": "short"}),
    ("/auth/password-reset/confirm", {"token": "opaque", "password": "x" * 101}),
])
async def test_malformed_account_inputs_are_rejected(client, endpoint, payload):
    assert (await client.post(endpoint, json=payload)).status_code == 422


async def test_account_requests_are_rate_limited(client, monkeypatch):
    import backend.rate_limit as rate_limit
    monkeypatch.setattr(rate_limit, "RATE_LIMIT_PER_MINUTE", 2)
    monkeypatch.setattr(rate_limit.time, "time", lambda: 1_000_000)
    for _ in range(2):
        assert (await client.post("/auth/password-reset/request", json={
            "email": "rate-limit@example.com",
        })).status_code == 202
    response = await client.post("/auth/password-reset/request", json={"email": "rate-limit@example.com"})
    assert response.status_code == 429
    assert 1 <= int(response.headers["Retry-After"]) <= 60


@pytest.fixture
def account_smtp(monkeypatch):
    from backend.tasks import email_tasks
    monkeypatch.setattr(email_tasks, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(email_tasks, "PUBLIC_APP_URL", "https://social.example.com")
    send = Mock(return_value=True)
    monkeypatch.setattr(email_tasks, "_send_email_sync", send)
    return send


@pytest.mark.parametrize("purpose,path", [("verify", "verify-email"), ("reset", "reset-password")])
async def test_account_worker_sends_fragment_link_and_records_success(client, accounts, db, account_smtp, purpose, path):
    from backend.tasks import email_tasks
    account, _ = accounts
    row, raw = await issue_token(client, db, account, purpose)
    delivery = await db.scalar(select(EmailDelivery).where(EmailDelivery.token_id == row.token_hash))
    assert await email_tasks._deliver_pending(db) == 1
    account_smtp.assert_called_once()
    _, body, recipient = account_smtp.call_args.args
    assert f"https://social.example.com/{path}#token={raw}" in body
    assert "?token=" not in body
    assert recipient == account["email"]
    await db.refresh(delivery)
    assert delivery.status == "sent"
    assert delivery.attempts == 1
    assert delivery.last_error is None
    await db.refresh(row)
    assert row.encrypted_secret is None


async def test_account_worker_retries_transient_failure_without_losing_token(client, accounts, db, account_smtp):
    from backend.tasks import email_tasks
    account, _ = accounts
    row, raw = await issue_token(client, db, account, "reset")
    delivery = await db.scalar(select(EmailDelivery).where(EmailDelivery.token_id == row.token_hash))
    account_smtp.side_effect = TimeoutError("timeout")
    assert await email_tasks._deliver_pending(db) == 1
    await db.refresh(delivery)
    assert delivery.status == "pending"
    assert delivery.attempts == 1
    assert delivery.available_at > datetime.now(timezone.utc)
    await db.refresh(row)
    assert row.consumed is False
    assert decrypt_secret(row.encrypted_secret) == raw
    assert await email_tasks._deliver_pending(db) == 0
    account_smtp.side_effect = None
    delivery.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()
    assert await email_tasks._deliver_pending(db) == 1
    await db.refresh(delivery)
    assert delivery.status == "sent"
    assert delivery.attempts == 2
    assert account_smtp.call_count == 2


@pytest.mark.parametrize("obsolete", ["expired", "reissued", "consumed"])
async def test_account_worker_skips_obsolete_links(client, accounts, db, account_smtp, obsolete):
    from backend.tasks import email_tasks
    account, _ = accounts
    row, raw = await issue_token(client, db, account, "verify")
    if obsolete == "expired":
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await db.commit()
    elif obsolete == "consumed":
        assert (await client.post("/auth/email-verification/confirm", json={"token": raw})).status_code == 204
    else:
        replacement, _ = await issue_token(client, db, account, "verify")
        # Keep the replacement out of this worker pass to isolate the old link.
        delivery = await db.scalar(select(EmailDelivery).where(EmailDelivery.token_id == replacement.token_hash))
        delivery.available_at = datetime.now(timezone.utc) + timedelta(minutes=1)
        await db.commit()
    await email_tasks._deliver_pending(db)
    delivery = await db.scalar(select(EmailDelivery).where(EmailDelivery.token_id == row.token_hash))
    assert delivery.status == "cancelled"
    assert delivery.attempts == 0
    await db.refresh(row)
    assert row.encrypted_secret is None
    account_smtp.assert_not_called()


@pytest.mark.parametrize("purpose,path", [("verify", "verify-email"), ("reset", "reset-password")])
async def test_link_forms_have_privacy_headers_and_get_does_not_consume(client, accounts, db, purpose, path):
    account, _ = accounts
    row, token = await issue_token(client, db, account, purpose)
    response = await client.get(f"/{path}#token={token}")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "text/html" in response.headers["Content-Type"]
    assert token not in response.text
    await db.refresh(row)
    assert row.consumed is False


async def test_two_connections_cannot_consume_the_same_reset_token_twice():
    import asyncio
    from uuid import uuid4

    from fastapi import HTTPException
    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from backend.account_tokens import consume_token, issue_token as create_account_token
    from backend.database import ASYNC_DATABASE_URL

    engine = create_async_engine(ASYNC_DATABASE_URL, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    user_id = None
    try:
        async with sessions() as seed:
            name = f"reset_race_{uuid4().hex}"
            user = User(username=name, email=f"{name}@example.com", hashed_password="unused")
            seed.add(user)
            await seed.flush()
            user_id = user.id
            await create_account_token(seed, user, "reset")
            row = await seed.scalar(select(AccountToken).where(AccountToken.user_id == user_id))
            raw, digest = decrypt_secret(row.encrypted_secret), row.token_hash
            await seed.commit()

        async def reset_once():
            async with sessions() as session:
                try:
                    user = await consume_token(session, raw, "reset")
                    user.token_version += 1
                    await session.commit()
                    return 204
                except HTTPException as exc:
                    await session.rollback()
                    return exc.status_code

        outcomes = await asyncio.wait_for(asyncio.gather(reset_once(), reset_once()), timeout=5)
        assert sorted(outcomes) == [204, 400]
        async with sessions() as check:
            assert (await check.get(User, user_id)).token_version == 1
            row = await check.get(AccountToken, digest)
            assert row.consumed is True
            assert row.encrypted_secret is None
            delivery = await check.scalar(select(EmailDelivery).where(EmailDelivery.token_id == digest))
            assert delivery.status == "cancelled"
    finally:
        try:
            async with sessions() as cleanup:
                if user_id is not None:
                    await cleanup.execute(delete(User).where(User.id == user_id))
                    await cleanup.commit()
        finally:
            await engine.dispose()


@pytest.mark.parametrize("email", [
    "one@example.com,two@example.com",
    "User Name <user@example.com>",
    "one@example.com;two@example.com",
])
async def test_signup_and_reset_reject_multi_recipient_and_display_names(client, email):
    assert (await client.post("/users", json={
        "username": "invalid_mailbox", "password": "test-password", "email": email,
    })).status_code == 422
    assert (await client.post("/auth/password-reset/request", json={"email": email})).status_code == 422


async def test_failed_logins_keep_rate_counters_after_authentication_error(client, accounts, monkeypatch):
    from types import SimpleNamespace
    import backend.rate_limit as rate_limit

    account, _ = accounts
    monkeypatch.setattr(rate_limit, "RATE_LIMIT_PER_MINUTE", 2)
    monkeypatch.setattr(rate_limit, "time", SimpleNamespace(time=lambda: 2_000_000))
    payload = {"username": account["username"], "password": "wrong-password"}
    assert (await client.post("/login", json=payload)).status_code == 401
    assert (await client.post("/login", json=payload)).status_code == 401
    blocked = await client.post("/login", json=payload)
    assert blocked.status_code == 429
    assert 1 <= int(blocked.headers["Retry-After"]) <= 60


@pytest.mark.parametrize("version_claim", [{}, {"version": None}, {"version": True},
                                         {"version": "0"}, {"version": 0.0},
                                         {"version": {}}, {"version": -1}, {"version": 1}])
async def test_signed_jwt_missing_or_invalid_version_is_rejected(client, accounts, version_claim):
    from jose import jwt
    from backend.config import ALGORITHM, SECRET_KEY

    account, _ = accounts
    common = {
        "sub": account["username"], "user_id": account["id"],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5), **version_claim,
    }
    access = jwt.encode({**common, "token_type": "access"}, SECRET_KEY, algorithm=ALGORITHM)
    refresh = jwt.encode({**common, "token_type": "refresh"}, SECRET_KEY, algorithm=ALGORITHM)
    assert (await client.get("/me", headers={"Authorization": f"Bearer {access}"})).status_code == 401
    assert (await client.post("/refresh", json={"refresh_token": refresh})).status_code == 401


async def test_login_waits_for_password_reset_and_rejects_old_password():
    import asyncio
    from uuid import uuid4

    from httpx import ASGITransport, AsyncClient
    from jose import jwt
    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from backend.config import ALGORITHM, SECRET_KEY
    from backend.database import ASYNC_DATABASE_URL, get_db
    from backend.main import api
    from backend.security import get_password_hash

    at_user_query = asyncio.Event()

    class LoginSession(AsyncSession):
        async def scalar(self, statement, *args, **kwargs):
            if any(column.get("entity") is User for column in getattr(statement, "column_descriptions", [])):
                at_user_query.set()
            return await super().scalar(statement, *args, **kwargs)

    engine = create_async_engine(ASYNC_DATABASE_URL, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    login_sessions = async_sessionmaker(engine, class_=LoginSession, expire_on_commit=False)
    name = f"login_reset_race_{uuid4().hex}"
    previous_overrides = api.dependency_overrides.copy()
    user_id = None
    login_task = None
    try:
        async with sessions() as seed:
            user = User(username=name, hashed_password=get_password_hash("old-password"))
            seed.add(user)
            await seed.commit()
            user_id = user.id

        async with login_sessions() as login_db, sessions() as reset_db:
            # Hold the old instance strongly: the login query must refresh it after waiting.
            old_user = await login_db.get(User, user_id)
            await login_db.commit()
            reset_user = await reset_db.scalar(select(User).where(User.id == user_id).with_for_update())
            reset_user.hashed_password = get_password_hash("new-password")
            reset_user.token_version = 1
            await reset_db.flush()

            async def override_db():
                yield login_db

            api.dependency_overrides[get_db] = override_db
            async with AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as http:
                login_task = asyncio.create_task(http.post("/login", json={
                    "username": name, "password": "old-password",
                }))
                await asyncio.wait_for(at_user_query.wait(), timeout=5)
                assert not login_task.done()
                await reset_db.commit()
                old_login = await asyncio.wait_for(login_task, timeout=5)
                assert old_login.status_code == 401
                assert old_user.token_version == 1
                new_login = await http.post("/login", json={"username": name, "password": "new-password"})
                assert new_login.status_code == 200
                payload = jwt.decode(new_login.json()["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
                assert payload["version"] == 1
                await login_db.rollback()
    finally:
        if login_task is not None and not login_task.done():
            login_task.cancel()
            await asyncio.gather(login_task, return_exceptions=True)
        api.dependency_overrides.clear()
        api.dependency_overrides.update(previous_overrides)
        try:
            async with sessions() as cleanup:
                if user_id is not None:
                    await cleanup.execute(delete(User).where(User.id == user_id))
                    await cleanup.commit()
        finally:
            await engine.dispose()
