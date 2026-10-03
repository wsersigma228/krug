import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy import select, update

from backend.config import SECRET_KEY
from backend.models import AccountToken, EmailDelivery, User


def cipher():
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest()))


def decrypt_secret(value: str) -> str:
    return cipher().decrypt(value.encode()).decode()


async def issue_token(db, user: User, purpose: str):
    old = select(AccountToken.token_hash).where(AccountToken.user_id == user.id, AccountToken.purpose == purpose)
    await db.execute(update(EmailDelivery).where(
        EmailDelivery.token_id.in_(old), EmailDelivery.status == "pending",
    ).values(status="cancelled"))
    await db.execute(update(AccountToken).where(
        AccountToken.user_id == user.id, AccountToken.purpose == purpose,
    ).values(consumed=True, encrypted_secret=None))
    raw = secrets.token_urlsafe(32)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    db.add(AccountToken(
        token_hash=digest, user_id=user.id, purpose=purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=60 if purpose == "verify" else 30),
        encrypted_secret=cipher().encrypt(raw.encode()).decode(),
    ))
    await db.flush()
    db.add(EmailDelivery(kind=purpose, token_id=digest, recipient_id=user.id))


async def consume_token(db, raw: str, purpose: str):
    digest = hashlib.sha256(raw.encode()).hexdigest()
    user_id = await db.scalar(select(AccountToken.user_id).where(AccountToken.token_hash == digest))
    if user_id is None:
        raise HTTPException(400, "Invalid or expired link")
    # All account changes lock user before token/delivery, including login and worker.
    user = await db.scalar(select(User).where(User.id == user_id).execution_options(populate_existing=True).with_for_update())
    token = await db.scalar(select(AccountToken).where(AccountToken.token_hash == digest)
                            .execution_options(populate_existing=True).with_for_update())
    if not user or not token or token.purpose != purpose or token.consumed or token.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(400, "Invalid or expired link")
    token.consumed = True
    token.encrypted_secret = None
    await db.execute(update(EmailDelivery).where(
        EmailDelivery.token_id == digest, EmailDelivery.status == "pending",
    ).values(status="cancelled"))
    return user
