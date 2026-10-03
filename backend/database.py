from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from backend.config import DATABASE_URL

# Alembic uses the sync driver; requests use the async variant.
ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg://", "postgresql+psycopg_async://")

engine = create_async_engine(ASYNC_DATABASE_URL)
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()


async def get_db():
    """Keep one session open for the request."""
    async with SessionLocal() as db:
        yield db
