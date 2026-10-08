"""Bounded importer for explicitly configured public GitLab.com projects."""
import asyncio
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import json
import logging
import re
from time import sleep
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.config import GITLAB_PROJECTS
from backend.database import ASYNC_DATABASE_URL
from backend.github_import import Repository, MAX_RESPONSE_BYTES, STALE_ACTIVITY_DAYS, STALE_VERIFICATION_DAYS, store_repository
from backend.models import Project

logger = logging.getLogger(__name__)
MAX_RETRY_AFTER_SECONDS = 30


class GitLabRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if parsed.scheme != "https" or parsed.netloc != "gitlab.com" or not parsed.path.startswith("/api/v4/projects/"):
            raise ValueError("Unexpected GitLab redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def normalize_project(data: dict, now: datetime) -> Repository:
    external_id = data.get("id")
    path = data.get("path_with_namespace")
    if type(external_id) is not int or external_id <= 0 or not isinstance(path, str) or not valid_project_path(path):
        raise ValueError("Invalid GitLab project identity")
    if data.get("visibility") != "public":
        raise ValueError("Only public projects may be imported")
    name = data.get("name")
    description = data.get("description") or ""
    if not isinstance(name, str) or not name.strip() or not isinstance(description, str):
        raise ValueError("Invalid GitLab project metadata")
    activity = data.get("last_activity_at")
    if activity is not None and not isinstance(activity, str):
        raise ValueError("Invalid GitLab project activity timestamp")
    activity_at = datetime.fromisoformat(activity.replace("Z", "+00:00")) if activity else None
    if activity_at is not None and activity_at.tzinfo is None:
        raise ValueError("Activity needs a timezone")
    topics = data.get("topics") or []
    if not isinstance(topics, list) or any(not isinstance(topic, str) for topic in topics):
        raise ValueError("Invalid GitLab project topics")
    status = "archived" if data.get("archived") else "active"
    if status == "active" and (activity_at is None or activity_at < now - timedelta(days=STALE_ACTIVITY_DAYS)):
        status = "stale"
    return Repository(
        str(external_id), f"gitlab-{external_id}", name.strip()[:200],
        description.strip()[:300] or f"{path} · GitLab project",
        f"https://gitlab.com/{path.lower()}",
        sorted({topic.strip().lower()[:40] for topic in topics if topic.strip()})[:20],
        [], activity_at, status,
    )


def valid_project_path(path: str) -> bool:
    segments = path.split("/")
    return len(segments) >= 2 and bool(re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*", path, re.ASCII)) and all(
        segment not in {".", ".."} for segment in segments
    )


def fetch_project(path: str, now: datetime) -> Repository:
    if not isinstance(path, str) or not valid_project_path(path):
        raise ValueError("Use a GitLab namespace/project path, not an arbitrary URL")
    url = f"https://gitlab.com/api/v4/projects/{quote(path, safe='')}?license=true"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "Krug-discovery"})
    opener = build_opener(GitLabRedirects())
    try:
        response = opener.open(request, timeout=15)
    except HTTPError as error:
        retry_after = error.headers.get("Retry-After") if error.code == 429 else None
        if retry_after is None:
            raise
        if retry_after.isascii() and retry_after.isdecimal():
            delay = int(retry_after)
        else:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                delay = max(0, int((retry_at - datetime.now(timezone.utc)).total_seconds()))
            except (TypeError, ValueError, OverflowError):
                raise error
        if delay > MAX_RETRY_AFTER_SECONDS:
            raise error
        sleep(delay)
        response = opener.open(request, timeout=15)
    with response:
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("GitLab project response is too large")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Expected GitLab project object")
    return normalize_project(data, now)


async def import_projects(db, paths: list[str] | None = None) -> dict:
    now = datetime.now(timezone.utc)
    paths = GITLAB_PROJECTS if paths is None else paths
    if len(paths) > 10:
        raise ValueError("A run supports at most 10 GitLab projects")
    if any(not isinstance(path, str) or not valid_project_path(path) for path in paths):
        raise ValueError("Use GitLab namespace/project paths")
    result = {"imported": 0, "failed": 0, "skipped": 0}
    if not await db.scalar(text("SELECT pg_try_advisory_xact_lock(731945, 2)")):
        return {**result, "busy": True}
    for path in paths:
        try:
            item = await asyncio.to_thread(fetch_project, path, now)
            async with db.begin_nested():
                stored = await store_repository(db, item, now, source_name="gitlab")
            result["imported" if stored else "skipped"] += 1
        except Exception as error:
            logger.warning("GitLab import failed (%s)", type(error).__name__)
            result["failed"] += 1
            if isinstance(error, HTTPError) and error.code in (403, 429):
                break
    await db.execute(update(Project).where(
        Project.origin == "external", Project.source_name == "gitlab",
        Project.status == "active", Project.claimed_at.is_(None),
        Project.last_verified_at < now - timedelta(days=STALE_VERIFICATION_DAYS),
    ).values(status="stale"))
    await db.commit()
    return result


async def run_import(paths: list[str] | None = None) -> dict:
    engine = create_async_engine(ASYNC_DATABASE_URL, poolclass=NullPool)
    try:
        async with async_sessionmaker(engine, autoflush=False, expire_on_commit=False)() as db:
            return await import_projects(db, paths)
    finally:
        await engine.dispose()
