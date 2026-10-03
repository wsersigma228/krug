import smtplib
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock

import bcrypt
import pytest
from sqlalchemy import select

from backend.models import EmailDelivery, User
from backend.tasks.celery_app import celery_app

from backend.security import get_password_hash, verify_password
from backend.tasks import email_tasks


def test_argon2_long_unicode_and_legacy_bcrypt():
    password = "пароль" * 15
    hashed = get_password_hash(password)
    assert hashed.startswith("$argon2")
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)
    legacy = bcrypt.hashpw(b"old-password", bcrypt.gensalt()).decode()
    assert verify_password("old-password", legacy)
    assert not verify_password("wrong", legacy)


def test_email_has_one_recipient(monkeypatch):
    smtp = MagicMock()
    server = smtp.return_value.__enter__.return_value
    monkeypatch.setattr(email_tasks.smtplib, "SMTP", smtp)
    monkeypatch.setattr(email_tasks, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(email_tasks, "SMTP_USER", "sender@example.com")
    assert email_tasks._send_email_sync("Subject", "Body", "alice@example.com")
    msg = server.send_message.call_args.args[0]
    assert msg["To"] == "alice@example.com"
    assert msg["Bcc"] is None
    server.starttls.assert_called_once()
    server.login.assert_called_once()


@pytest.fixture
async def pending_delivery(client, accounts, db):
    author, reader = accounts
    user = await db.get(User, reader["id"])
    user.email_verified = True
    await db.commit()
    assert (await client.patch("/me/notifications", headers=reader["headers"], json={
        "email_publications": True,
    })).status_code == 200
    await client.post("/subscriptions", headers=reader["headers"], json={"author_id": author["id"]})
    response = await client.post("/posts", headers=author["headers"], json={
        "title": "Email publication", "content": "Body", "is_published": True,
    })
    assert response.status_code == 201, response.text
    post = response.json()
    delivery = (await db.scalars(select(EmailDelivery).where(EmailDelivery.post_id == post["id"]))).one()
    return author, reader, post, delivery


@pytest.fixture
def smtp_sender(monkeypatch):
    monkeypatch.setattr(email_tasks, "SMTP_HOST", "smtp.example.com")
    send = Mock(return_value=True)
    monkeypatch.setattr(email_tasks, "_send_email_sync", send)
    return send


@pytest.mark.parametrize("error", [
    TimeoutError("timeout"), smtplib.SMTPServerDisconnected("lost"),
    smtplib.SMTPDataError(451, b"try later"),
    smtplib.SMTPRecipientsRefused({"reader@example.com": (450, b"try later")}),
])
async def test_transient_delivery_retries_then_succeeds(db, pending_delivery, smtp_sender, error):
    _, reader, _, delivery = pending_delivery
    smtp_sender.side_effect = error
    await email_tasks._deliver_pending(db)
    await db.refresh(delivery)
    assert delivery.status == "pending"
    assert delivery.attempts == 1
    assert delivery.available_at > datetime.now(timezone.utc)
    assert delivery.last_error
    await email_tasks._deliver_pending(db)
    assert smtp_sender.call_count == 1
    delivery.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()
    smtp_sender.side_effect = None
    await email_tasks._deliver_pending(db)
    await db.refresh(delivery)
    assert delivery.status == "sent"
    assert smtp_sender.call_args.args[2] == reader["email"]
    await email_tasks._deliver_pending(db)
    assert smtp_sender.call_count == 2


@pytest.mark.parametrize("error", [
    smtplib.SMTPAuthenticationError(535, b"bad credentials"),
    smtplib.SMTPDataError(550, b"rejected"),
    smtplib.SMTPRecipientsRefused({"reader@example.com": (550, b"unknown recipient")}),
    smtplib.SMTPException("SMTP failed"),
    ValueError("Header values may not contain linefeed characters"),
])
async def test_permanent_delivery_fails_without_resend(db, pending_delivery, smtp_sender, error):
    _, _, _, delivery = pending_delivery
    smtp_sender.side_effect = error
    await email_tasks._deliver_pending(db)
    await db.refresh(delivery)
    assert delivery.status == "failed"
    assert delivery.attempts == 1
    assert delivery.last_error
    await email_tasks._deliver_pending(db)
    smtp_sender.assert_called_once()


async def test_disabled_smtp_keeps_pending_delivery(db, pending_delivery, smtp_sender, monkeypatch):
    _, _, _, delivery = pending_delivery
    monkeypatch.setattr(email_tasks, "SMTP_HOST", "")
    await email_tasks._deliver_pending(db)
    await db.refresh(delivery)
    assert delivery.status == "pending"
    assert delivery.attempts == 0
    smtp_sender.assert_not_called()


async def test_bad_header_does_not_block_later_deliveries(db, pending_delivery, smtp_sender):
    _, reader, post, first = pending_delivery
    second = EmailDelivery(publication_id="valid-next", post_id=post["id"], recipient_id=reader["id"])
    db.add(second)
    await db.commit()
    smtp_sender.side_effect = [ValueError("invalid email header"), True]
    await email_tasks._deliver_pending(db)
    await db.refresh(first)
    await db.refresh(second)
    assert first.status == "failed"
    assert second.status == "sent"


@pytest.mark.parametrize("change", ["hide", "unsubscribe"])
async def test_obsolete_delivery_is_cancelled(client, db, pending_delivery, smtp_sender, change):
    author, reader, post, delivery = pending_delivery
    if change == "hide":
        response = await client.put(f"/posts/{post['id']}", headers=author["headers"], json={"is_published": False})
    else:
        response = await client.delete(f"/subscriptions/{author['id']}", headers=reader["headers"])
    assert response.status_code in (200, 204)
    await email_tasks._deliver_pending(db)
    await db.refresh(delivery)
    assert delivery.status == "cancelled"
    smtp_sender.assert_not_called()


async def test_republication_replaces_pending_delivery(client, db, pending_delivery, smtp_sender):
    author, reader, post, delivery = pending_delivery
    url = f"/posts/{post['id']}"
    assert (await client.put(url, headers=author["headers"], json={"is_published": False})).status_code == 200
    assert (await client.put(url, headers=author["headers"], json={"is_published": True})).status_code == 200
    await email_tasks._deliver_pending(db)
    deliveries = (await db.scalars(select(EmailDelivery).where(EmailDelivery.post_id == post["id"]).order_by(EmailDelivery.id))).all()
    assert [row.status for row in deliveries] == ["cancelled", "sent"]
    assert deliveries[0].publication_id != deliveries[1].publication_id
    assert deliveries[1].recipient_id == reader["id"]
    smtp_sender.assert_called_once()


@pytest.mark.parametrize("target", ["post", "recipient", "author"])
async def test_deleted_entities_remove_deliveries(client, db, pending_delivery, target):
    author, reader, post, delivery = pending_delivery
    url, headers = {
        "post": (f"/posts/{post['id']}", author["headers"]),
        "recipient": (f"/users/{reader['id']}", reader["headers"]),
        "author": (f"/users/{author['id']}", author["headers"]),
    }[target]
    assert (await client.delete(url, headers=headers)).status_code == 204
    assert (await db.scalars(select(EmailDelivery).where(EmailDelivery.id == delivery.id))).all() == []


async def test_delivery_batch_is_bounded(db, pending_delivery, smtp_sender):
    _, reader, post, _ = pending_delivery
    db.add_all([EmailDelivery(publication_id=f"batch-{i}", post_id=post["id"], recipient_id=reader["id"]) for i in range(21)])
    await db.commit()
    await email_tasks._deliver_pending(db)
    deliveries = (await db.scalars(select(EmailDelivery).where(EmailDelivery.post_id == post["id"]))).all()
    assert sum(row.status == "sent" for row in deliveries) == 20
    assert sum(row.status == "pending" for row in deliveries) == 2
    assert smtp_sender.call_count == 20


def test_delivery_task_uses_configured_broker_and_beat():
    from backend.config import REDIS_URL
    assert email_tasks.deliver_pending_emails.app.conf.broker_url == REDIS_URL
    schedule = celery_app.conf.beat_schedule["deliver-pending-emails"]
    assert schedule["task"] == email_tasks.deliver_pending_emails.name
    assert schedule["schedule"] > 0


async def test_locked_delivery_does_not_block_another_post(smtp_sender):
    import asyncio
    from uuid import uuid4

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from backend.database import ASYNC_DATABASE_URL
    from backend.models import Post, Subscription, User

    engine = create_async_engine(ASYNC_DATABASE_URL, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    name = f"concurrent_{uuid4().hex}"
    user_ids = []
    try:
        async with sessions() as seed:
            author = User(username=f"{name}_author", hashed_password="unused")
            reader = User(username=f"{name}_reader", hashed_password="unused", email=f"{name}@example.com",
                          email_verified=True, email_publications=True)
            seed.add_all([author, reader])
            await seed.flush()
            user_ids = [author.id, reader.id]
            seed.add(Subscription(author_id=author.id, subscriber_id=reader.id))
            posts = [Post(author_id=author.id, title=f"Locked post {i}", content="Body", is_published=True) for i in range(2)]
            seed.add_all(posts)
            await seed.flush()
            due = datetime.now(timezone.utc) - timedelta(days=1)
            deliveries = [EmailDelivery(
                publication_id=str(uuid4()), post_id=post.id, recipient_id=reader.id,
                available_at=due + timedelta(seconds=i),
            ) for i, post in enumerate(posts)]
            seed.add_all(deliveries)
            await seed.commit()
            first_id, second_id = [row.id for row in deliveries]

        async with sessions() as first_worker, sessions() as second_worker:
            await first_worker.execute(
                select(EmailDelivery, Post).join(Post, Post.id == EmailDelivery.post_id)
                .where(EmailDelivery.id == first_id)
                .with_for_update(of=[EmailDelivery, Post])
            )
            await asyncio.wait_for(email_tasks._deliver_pending(second_worker), timeout=5)
            assert (await second_worker.get(EmailDelivery, first_id)).status == "pending"
            assert (await second_worker.get(EmailDelivery, second_id)).status == "sent"
            smtp_sender.assert_called_once()
            assert "Locked post 1" in smtp_sender.call_args.args[0]

            await first_worker.rollback()
            await asyncio.wait_for(email_tasks._deliver_pending(second_worker), timeout=5)
            first = await second_worker.get(EmailDelivery, first_id)
            await second_worker.refresh(first)
            assert first.status == "sent"
            assert smtp_sender.call_count == 2
            assert "Locked post 0" in smtp_sender.call_args.args[0]
            await email_tasks._deliver_pending(second_worker)
            assert smtp_sender.call_count == 2
    finally:
        try:
            async with sessions() as cleanup:
                if user_ids:
                    await cleanup.execute(delete(Post).where(Post.author_id == user_ids[0]))
                    await cleanup.execute(delete(Subscription).where(Subscription.author_id == user_ids[0]))
                    await cleanup.execute(delete(User).where(User.id.in_(user_ids)))
                    await cleanup.commit()
        finally:
            await engine.dispose()
