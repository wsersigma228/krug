import asyncio
import logging
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL, SMTP_STARTTLS, PUBLIC_APP_URL
from backend.database import ASYNC_DATABASE_URL
from backend.models import EmailDelivery, Post, User, Subscription, AccountToken
from backend.account_tokens import decrypt_secret
from cryptography.fernet import InvalidToken
from backend.schemas import validate_email_address
from backend.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(autoretry_for=(OperationalError,), retry_kwargs={"max_retries": 3}, retry_backoff=60)
def deliver_pending_emails():
    return asyncio.run(_run_deliveries())


async def _run_deliveries():
    # Connections must not outlive this task's event loop.
    engine = create_async_engine(ASYNC_DATABASE_URL, poolclass=NullPool)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            return await _deliver_pending(db)
    finally:
        await engine.dispose()


async def _deliver_pending(db):
    if not SMTP_HOST:
        return 0
    processed = 0
    for _ in range(20):
        account_user = await db.scalar(
            select(User).join(EmailDelivery, EmailDelivery.recipient_id == User.id)
            .where(EmailDelivery.kind != "publication", EmailDelivery.status == "pending",
                   EmailDelivery.available_at <= datetime.now(timezone.utc))
            .order_by(EmailDelivery.available_at, EmailDelivery.id).limit(1)
            .execution_options(populate_existing=True).with_for_update(of=User, skip_locked=True)
        )
        if account_user:
            delivery = await db.scalar(select(EmailDelivery).where(
                EmailDelivery.recipient_id == account_user.id, EmailDelivery.kind != "publication",
                EmailDelivery.status == "pending", EmailDelivery.available_at <= datetime.now(timezone.utc),
            ).order_by(EmailDelivery.available_at, EmailDelivery.id).limit(1).with_for_update())
            if delivery is None:
                await db.commit()
                continue
            token = await db.get(AccountToken, delivery.token_id, populate_existing=True)
            if token.consumed or token.expires_at <= datetime.now(timezone.utc) or not account_user.email:
                delivery.status = "cancelled"
                token.encrypted_secret = None
            else:
                try:
                    raw = decrypt_secret(token.encrypted_secret)
                except (InvalidToken, AttributeError):
                    delivery.status = "failed"
                    delivery.last_error = "InvalidToken"
                else:
                    path = "verify-email" if delivery.kind == "verify" else "reset-password"
                    russian = account_user.language == "ru"
                    subject = (
                        "Подтвердите email" if delivery.kind == "verify" else "Сброс пароля"
                    ) if russian else (
                        "Verify your email" if delivery.kind == "verify" else "Reset your password"
                    )
                    notice = (
                        "Срок действия ссылки ограничен. Если вы не запрашивали её, проигнорируйте письмо."
                        if russian else "This link expires; ignore it if you did not request it."
                    )
                    # URL fragment prevents tokens being sent in HTTP access logs.
                    language_query = f"?lang={account_user.language}" if account_user.language else ""
                    body = f"{subject}:\n\n{PUBLIC_APP_URL}/{path}{language_query}#token={raw}\n\n{notice}"
                    await _attempt_delivery(delivery, subject, body, account_user.email)
                    if delivery.status == "sent":
                        token.encrypted_secret = None
            await db.commit()
            processed += 1
            continue
        # ponytail: post locks serialize mail for one post during SMTP;
        # use delivery leases if measured throughput requires parallel sends.
        row = (await db.execute(
            select(EmailDelivery, Post, User)
            .join(Post, Post.id == EmailDelivery.post_id)
            .join(User, User.id == EmailDelivery.recipient_id)
            .where(EmailDelivery.kind == "publication", EmailDelivery.status == "pending", EmailDelivery.available_at <= datetime.now(timezone.utc))
            .order_by(EmailDelivery.available_at, EmailDelivery.id)
            .execution_options(populate_existing=True)
            .limit(1).with_for_update(of=[EmailDelivery, Post], skip_locked=True)
        )).first()
        if not row:
            await db.commit()
            break
        delivery, post, recipient = row
        recipient = await db.scalar(select(User).where(User.id == recipient.id)
                                    .execution_options(populate_existing=True).with_for_update(nowait=True))
        if recipient is None:
            delivery.status = "cancelled"
            await db.commit()
            processed += 1
            continue
        subscription = await db.scalar(select(Subscription).where(
            Subscription.author_id == post.author_id,
            Subscription.subscriber_id == recipient.id,
        ).with_for_update(nowait=True))
        if not post.is_published or not subscription or not recipient.email or not recipient.email_verified or not recipient.email_publications:
            delivery.status = "cancelled"
        else:
            author = await db.get(User, post.author_id)
            if recipient.language == "ru":
                subject = f"Новая публикация от {author.username}: {post.title}"
                body = f'Здравствуйте!\n\n{author.username} опубликовал новую запись:\n\n"{post.title}"\n\n-- Команда Круга'
            else:
                subject = f"New post from {author.username}: {post.title}"
                body = f'Hello!\n\n{author.username} just published a new post:\n\n"{post.title}"\n\n-- Blog Team'
            await _attempt_delivery(delivery, subject, body, recipient.email)
        # A later recipient's failure must not roll back an earlier successful send.
        await db.commit()
        processed += 1
    return processed


async def _attempt_delivery(delivery, subject, body, recipient):
    delivery.attempts += 1
    try:
        await asyncio.to_thread(_send_email_sync, subject, body, recipient)
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        code = getattr(exc, "smtp_code", None)
        if isinstance(exc, smtplib.SMTPRecipientsRefused):
            code = next(iter(exc.recipients.values()), (None, ""))[0]
        transient = (
            isinstance(exc, OSError) and not isinstance(exc, smtplib.SMTPException)
        ) or isinstance(exc, smtplib.SMTPServerDisconnected) or (code is not None and 400 <= code < 500)
        delivery.last_error = f"{type(exc).__name__}:{code}"
        if transient:
            delivery.available_at = datetime.now(timezone.utc) + timedelta(seconds=min(3600, 60 * 2 ** min(delivery.attempts - 1, 6)))
        else:
            delivery.status = "failed"
        logger.warning("Email delivery %s: %s (%s)", delivery.id, delivery.status, delivery.last_error)
    else:
        delivery.status = "sent"
        delivery.last_error = None


def _send_email_sync(subject: str, body: str, recipient: str) -> bool:
    if not SMTP_HOST:
        return False
    recipient = validate_email_address(recipient)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL or SMTP_USER
    msg["To"] = recipient
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        if SMTP_STARTTLS:
            server.starttls(context=ssl.create_default_context())
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
    return True
