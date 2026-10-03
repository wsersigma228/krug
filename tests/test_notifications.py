from unittest.mock import Mock

import pytest
from sqlalchemy import select

from backend.models import EmailDelivery, User
from backend.tasks import email_tasks


async def set_preference(client, account, enabled):
    return await client.patch("/me/notifications", headers=account["headers"], json={
        "email_publications": enabled,
    })


async def verify_and_enable(client, db, account):
    user = await db.get(User, account["id"])
    user.email_verified = True
    await db.commit()
    response = await set_preference(client, account, True)
    assert response.status_code == 200, response.text


async def publish(client, author):
    response = await client.post("/posts", headers=author["headers"], json={
        "title": "Notification", "content": "Body", "is_published": True,
    })
    assert response.status_code == 201, response.text
    return response.json()


async def test_publication_email_is_disabled_by_default_without_affecting_feed(client, accounts, db):
    author, reader = accounts
    assert (await client.get("/me/notifications", headers=reader["headers"])).json() == {"email_publications": False}
    assert (await client.get("/me", headers=reader["headers"])).json()["email_publications"] is False
    assert (await client.post("/subscriptions", headers=reader["headers"], json={"author_id": author["id"]})).status_code == 201
    post = await publish(client, author)
    assert (await db.scalars(select(EmailDelivery).where(EmailDelivery.post_id == post["id"]))).all() == []
    assert [item["id"] for item in (await client.get("/feed", headers=reader["headers"])).json()["items"]] == [post["id"]]


@pytest.mark.parametrize("missing", ["verification", "email"])
async def test_enabling_requires_verified_present_email(client, accounts, db, missing):
    _, reader = accounts
    if missing == "email":
        user = await db.get(User, reader["id"])
        user.email = None
        user.email_verified = True
        await db.commit()
    assert (await set_preference(client, reader, True)).status_code == 403
    assert (await client.get("/me/notifications", headers=reader["headers"])).json() == {"email_publications": False}
    assert (await set_preference(client, reader, False)).status_code == 200


async def test_opt_in_persists_across_sessions_and_only_changes_owner(client, accounts, db):
    author, reader = accounts
    await verify_and_enable(client, db, reader)
    tokens = (await client.post("/login", json={"username": reader["username"], "password": "test-password"})).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert (await client.get("/me/notifications", headers=headers)).json() == {"email_publications": True}
    assert (await client.get("/me", headers=headers)).json()["email_publications"] is True
    assert (await client.get("/me/notifications", headers=author["headers"])).json() == {"email_publications": False}


@pytest.mark.parametrize("verified,opted_in", [(True, False), (False, True)])
async def test_publication_requires_both_consent_and_verification(client, accounts, db, verified, opted_in):
    author, reader = accounts
    user = await db.get(User, reader["id"])
    user.email_verified, user.email_publications = verified, opted_in
    await db.commit()
    await client.post("/subscriptions", headers=reader["headers"], json={"author_id": author["id"]})
    post = await publish(client, author)
    assert (await db.scalars(select(EmailDelivery).where(EmailDelivery.post_id == post["id"]))).all() == []


async def test_opt_out_cancels_publication_but_preserves_service_mail_and_subscription(client, accounts, db):
    author, reader = accounts
    await verify_and_enable(client, db, reader)
    await client.post("/subscriptions", headers=reader["headers"], json={"author_id": author["id"]})
    first = await publish(client, author)
    assert (await client.post("/auth/password-reset/request", json={"email": reader["email"]})).status_code == 202
    assert (await set_preference(client, reader, False)).json() == {"email_publications": False}
    deliveries = (await db.scalars(select(EmailDelivery).where(EmailDelivery.recipient_id == reader["id"]))).all()
    assert {delivery.kind: delivery.status for delivery in deliveries} == {"publication": "cancelled", "reset": "pending"}
    subscriptions = (await client.get("/subscriptions", headers=reader["headers"])).json()["items"]
    assert [item["id"] for item in subscriptions] == [author["id"]]
    second = await publish(client, author)
    assert (await db.scalars(select(EmailDelivery).where(EmailDelivery.post_id == second["id"]))).all() == []
    feed = (await client.get("/feed", headers=reader["headers"])).json()["items"]
    assert {item["id"] for item in feed} == {first["id"], second["id"]}
    assert (await set_preference(client, reader, True)).status_code == 200
    old = await db.scalar(select(EmailDelivery).where(EmailDelivery.post_id == first["id"]))
    assert old.status == "cancelled"
    third = await publish(client, author)
    new = await db.scalar(select(EmailDelivery).where(EmailDelivery.post_id == third["id"]))
    assert new.status == "pending"


@pytest.mark.parametrize("changed", ["email_publications", "email_verified"])
async def test_worker_rechecks_consent_and_verification_before_sending(client, accounts, db, monkeypatch, changed):
    author, reader = accounts
    await verify_and_enable(client, db, reader)
    await client.post("/subscriptions", headers=reader["headers"], json={"author_id": author["id"]})
    post = await publish(client, author)
    user = await db.get(User, reader["id"])
    setattr(user, changed, False)
    await db.commit()
    send = Mock(return_value=True)
    monkeypatch.setattr(email_tasks, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(email_tasks, "_send_email_sync", send)
    await email_tasks._deliver_pending(db)
    delivery = await db.scalar(select(EmailDelivery).where(EmailDelivery.post_id == post["id"]))
    assert delivery.status == "cancelled"
    assert delivery.attempts == 0
    send.assert_not_called()


@pytest.mark.parametrize("value", [None, 0, 1, "true", "false", [], {}])
async def test_notification_preference_requires_boolean(client, accounts, value):
    _, reader = accounts
    assert (await set_preference(client, reader, value)).status_code == 422


async def test_notification_settings_require_authentication_and_field(client, accounts):
    _, reader = accounts
    for method in [client.get, client.patch]:
        kwargs = {"json": {"email_publications": False}} if method == client.patch else {}
        assert (await method("/me/notifications", **kwargs)).status_code in (401, 403)
        assert (await method("/me/notifications", headers={"Authorization": "Bearer invalid"}, **kwargs)).status_code == 401
    assert (await client.patch("/me/notifications", headers=reader["headers"], json={})).status_code == 422


async def test_mutual_followers_can_publish_concurrently_without_deadlock():
    import asyncio
    from uuid import uuid4

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from backend.crud.posts import record_publication_emails
    from backend.database import ASYNC_DATABASE_URL
    from backend.models import Post, Subscription

    engine = create_async_engine(ASYNC_DATABASE_URL, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    user_ids = []
    try:
        async with sessions() as seed:
            name = f"mutual_publish_{uuid4().hex}"
            users = [User(
                username=f"{name}_{i}", email=f"{name}_{i}@example.com", hashed_password="unused",
                email_verified=True, email_publications=True,
            ) for i in range(2)]
            seed.add_all(users)
            await seed.flush()
            user_ids = [user.id for user in users]
            seed.add_all([
                Subscription(author_id=user_ids[0], subscriber_id=user_ids[1]),
                Subscription(author_id=user_ids[1], subscriber_id=user_ids[0]),
            ])
            await seed.commit()

        async with sessions() as first, sessions() as second:
            posts = [Post(author_id=user_id, title="Concurrent publication", content="Body", is_published=True)
                     for user_id in user_ids]
            first.add(posts[0])
            second.add(posts[1])
            # Each insert holds a foreign-key key-share lock on its own author.
            # Fanout must also lock the opposite recipient without conflicting with it.
            await first.flush()
            await second.flush()

            async def publish_in_transaction(session, post):
                await record_publication_emails(session, post)
                await session.commit()

            await asyncio.wait_for(asyncio.gather(
                publish_in_transaction(first, posts[0]),
                publish_in_transaction(second, posts[1]),
            ), timeout=5)
            post_ids = [post.id for post in posts]

        async with sessions() as check:
            deliveries = (await check.scalars(select(EmailDelivery).where(
                EmailDelivery.post_id.in_(post_ids),
            ))).all()
            assert {(delivery.post_id, delivery.recipient_id, delivery.status) for delivery in deliveries} == {
                (post_ids[0], user_ids[1], "pending"),
                (post_ids[1], user_ids[0], "pending"),
            }
    finally:
        try:
            async with sessions() as cleanup:
                if user_ids:
                    await cleanup.execute(delete(Post).where(Post.author_id.in_(user_ids)))
                    await cleanup.execute(delete(Subscription).where(Subscription.author_id.in_(user_ids)))
                    await cleanup.execute(delete(User).where(User.id.in_(user_ids)))
                    await cleanup.commit()
        finally:
            await engine.dispose()
