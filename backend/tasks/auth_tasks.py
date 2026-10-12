import asyncio
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.database import ASYNC_DATABASE_URL
from backend.models import RefreshToken
from backend.tasks.celery_app import celery_app


@celery_app.task
def purge_expired_refresh_tokens():
    return asyncio.run(_run_purge())


async def _run_purge():
    # Connections must not outlive this task's event loop.
    engine = create_async_engine(ASYNC_DATABASE_URL, poolclass=NullPool)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            return await purge_expired(db)
    finally:
        await engine.dispose()


async def purge_expired(db) -> int:
    result = await db.execute(delete(RefreshToken).where(RefreshToken.expires_at < datetime.now(timezone.utc)))
    await db.commit()
    return result.rowcount
