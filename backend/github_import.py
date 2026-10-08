"""Bounded GitHub metadata import; never infer team size or recruitment."""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import logging
import os
import re
from urllib.error import HTTPError
from urllib.request import Request, HTTPRedirectHandler, build_opener

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.database import ASYNC_DATABASE_URL
from backend.models import Project

logger = logging.getLogger(__name__)
DEFAULT_REPOSITORIES = (
    "godotengine/godot", "bevyengine/bevy", "excalidraw/excalidraw",
    "penpot/penpot", "fastapi/fastapi", "sveltejs/svelte",
    "django/django", "gdquest/learn-gdscript",
)
MAX_RESPONSE_BYTES = 512 * 1024
STALE_ACTIVITY_DAYS = 180
STALE_VERIFICATION_DAYS = 7


class GitHubRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith("https://api.github.com/repos/"):
            raise ValueError("Unexpected GitHub redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@dataclass(frozen=True)
class Repository:
    external_id: str
    slug: str
    title: str
    summary: str
    url: str
    tags: list[str]
    skills: list[str]
    activity_at: datetime | None
    status: str


def normalize_repository(data: dict, now: datetime) -> Repository:
    external_id = data.get("id")
    name = data.get("full_name", "")
    if type(external_id) is not int or external_id <= 0 or not re.fullmatch(r"[\w.-]+/[\w.-]+", name, re.ASCII):
        raise ValueError("Invalid repository identity")
    if data.get("private") is not False:
        raise ValueError("Only public repositories may be imported")
    description = data.get("description") or ""
    if not isinstance(description, str):
        raise ValueError("Invalid repository description")
    activity = data.get("pushed_at")
    activity_at = datetime.fromisoformat(activity.replace("Z", "+00:00")) if activity else None
    if activity_at is not None and activity_at.tzinfo is None:
        raise ValueError("Activity needs a timezone")
    topics = data.get("topics") or []
    if not isinstance(topics, list) or any(not isinstance(topic, str) for topic in topics):
        raise ValueError("Invalid repository topics")
    language = data.get("language")
    if language is not None and not isinstance(language, str):
        raise ValueError("Invalid repository language")
    status = "archived" if data.get("archived") or data.get("disabled") else "active"
    if status == "active" and (activity_at is None or activity_at < now - timedelta(days=STALE_ACTIVITY_DAYS)):
        status = "stale"
    return Repository(
        str(external_id), f"github-{external_id}", name[:200],
        description.strip()[:300] or f"{name} · GitHub repository",
        f"https://github.com/{name.lower()}",
        sorted({topic.strip().lower()[:40] for topic in topics if topic.strip()})[:20],
        [language.strip().lower()[:40]] if language else [], activity_at, status,
    )


def fetch_repository(name: str, now: datetime) -> Repository:
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", name, re.ASCII):
        raise ValueError("Use owner/repository, not an arbitrary URL")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Krug-discovery"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"https://api.github.com/repos/{name}", headers=headers)
    with build_opener(GitHubRedirects()).open(request, timeout=15) as response:
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("Repository response is too large")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Expected repository object")
    return normalize_repository(data, now)


async def store_repository(db, item: Repository, now: datetime, source_name: str = "github") -> bool:
    existing = await db.scalar(select(Project).where(Project.canonical_url == item.url))
    if existing and existing.origin == "native":
        return False
    values = dict(
        slug=item.slug, title=item.title, summary=item.summary, description=item.summary,
        origin="external", owner_id=None, visibility="public", status=item.status,
        stage="unknown", tags=item.tags, skills=item.skills, source_name=source_name,
        source_url=item.url, canonical_url=item.url, source_external_id=item.external_id,
        last_activity_at=item.activity_at, last_verified_at=now,
    )
    statement = insert(Project).values(**values)
    # Preserve all curator-owned fields after an external project has been claimed.
    changes = {key: value for key, value in values.items() if key not in {"slug", "origin", "owner_id"}}
    changes["updated_at"] = now
    await db.execute(statement.on_conflict_do_update(
        index_elements=[Project.source_name, Project.source_external_id], set_=changes,
        where=(Project.origin == "external") & Project.claimed_at.is_(None),
    ))
    return True


async def import_repositories(db, names: list[str] | None = None) -> dict:
    now = datetime.now(timezone.utc)
    if names is None:
        names = [name.strip() for name in os.getenv("GITHUB_REPOSITORIES", ",".join(DEFAULT_REPOSITORIES)).split(",") if name.strip()]
    if len(names) > 20:
        raise ValueError("A run supports at most 20 repositories")
    result = {"imported": 0, "failed": 0, "skipped": 0}
    # Transaction-scoped singleton; releases automatically even after worker failure.
    if not await db.scalar(text("SELECT pg_try_advisory_xact_lock(731945, 1)")):
        return {**result, "busy": True}
    for name in names:
        try:
            item = await asyncio.to_thread(fetch_repository, name, now)
            async with db.begin_nested():
                stored = await store_repository(db, item, now)
            result["imported" if stored else "skipped"] += 1
        except Exception as error:
            # Never log request headers, response content or credentials.
            logger.warning("GitHub import failed (%s)", type(error).__name__)
            result["failed"] += 1
            if isinstance(error, HTTPError) and error.code in (403, 429):
                break
    await db.execute(update(Project).where(
        Project.origin == "external", Project.source_name == "github",
        Project.status == "active", Project.claimed_at.is_(None),
        Project.last_verified_at < now - timedelta(days=STALE_VERIFICATION_DAYS),
    ).values(status="stale"))
    await db.commit()
    return result


async def run_import(names: list[str] | None = None) -> dict:
    # Celery runs each task in a new event loop, so task connections must not be pooled across runs.
    engine = create_async_engine(ASYNC_DATABASE_URL, poolclass=NullPool)
    try:
        async with async_sessionmaker(engine, autoflush=False, expire_on_commit=False)() as db:
            return await import_repositories(db, names)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repositories", nargs="*", help="owner/repository; defaults to configured shortlist")
    args = parser.parse_args()
    print(asyncio.run(run_import(args.repositories or None)))
