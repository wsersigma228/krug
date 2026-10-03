import hashlib
import hmac
import time

from fastapi import HTTPException, Request
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from backend.config import SECRET_KEY, RATE_LIMIT_PER_MINUTE
from backend.models import AuthRateLimit


async def check_rate_limit(db, request: Request, scope: str, identity: str = ""):
    now = int(time.time())
    bucket = now // 60
    # Trust the socket peer, not a user-supplied forwarding header.
    identifiers = [f"ip:{request.client.host if request.client else 'unknown'}"]
    if identity:
        identifiers.append(f"account:{identity.casefold()}")
    exceeded = False
    await db.execute(delete(AuthRateLimit).where(AuthRateLimit.bucket < bucket - 2))
    for identifier in identifiers:
        key = hmac.new(SECRET_KEY.encode(), f"{scope}:{identifier}".encode(), hashlib.sha256).hexdigest()
        statement = insert(AuthRateLimit).values(key=key, bucket=bucket, count=1)
        count = await db.scalar(statement.on_conflict_do_update(
            index_elements=[AuthRateLimit.key, AuthRateLimit.bucket],
            set_={"count": AuthRateLimit.count + 1},
        ).returning(AuthRateLimit.count))
        exceeded |= count > RATE_LIMIT_PER_MINUTE
    # Failed credentials and HTTP errors must not roll back the counters.
    await db.commit()
    if exceeded:
        raise HTTPException(429, "Too many requests", headers={"Retry-After": str(60 - now % 60)})
