from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.config import REDIS_URL
from redis.asyncio import Redis
from backend.routes import posts, users, media, social, projects

api = FastAPI()

api.include_router(projects.router)
api.include_router(posts.router)
api.include_router(users.router)
api.include_router(media.router)
api.include_router(social.router)
api.mount("/assets", StaticFiles(directory=Path(__file__).resolve().parent.parent / "frontend"), name="assets")


@api.get("/app", include_in_schema=False)
@api.get("/app/", include_in_schema=False)
def frontend_page():
    return users.account_link_page()


@api.get("/")
def home():
    """Process health check; does not check dependencies."""
    return {"ok": True}


@api.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    """Readiness of PostgreSQL and the mail broker, without returning connection details."""
    try:
        await db.execute(text("SELECT 1"))
        async with Redis.from_url(REDIS_URL, socket_timeout=2, socket_connect_timeout=2) as redis:
            await redis.ping()
    except Exception:
        raise HTTPException(503, "Dependency unavailable") from None
    return {"ok": True}
