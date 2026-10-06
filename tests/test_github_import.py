import asyncio
from datetime import datetime, timedelta, timezone
from time import time_ns

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.database import ASYNC_DATABASE_URL
from backend.github_import import normalize_repository, store_repository
from backend.models import Project
from backend.tasks.github_tasks import import_github


def repository(**changes):
    return {
        "id": 987654321, "full_name": "Example/Project", "private": False,
        "description": "A collaborative drawing tool", "topics": ["drawing", "drawing"],
        "language": "TypeScript", "pushed_at": "2026-10-01T00:00:00Z", **changes,
    }


def test_normalization_never_infers_recruitment():
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)
    item = normalize_repository(repository(), now)
    assert item.url == "https://github.com/example/project"
    assert item.tags == ["drawing"] and item.skills == ["typescript"]
    assert item.status == "active"
    assert normalize_repository(repository(description=None), now).summary == "Example/Project · GitHub repository"
    assert normalize_repository(repository(archived=True), now).status == "archived"
    assert normalize_repository(repository(pushed_at=None), now).status == "stale"
    assert normalize_repository(repository(), now + timedelta(days=181)).status == "stale"
    for changes in ({"private": True}, {"id": True}, {"full_name": "../../bad"}, {"topics": [{}]}):
        with pytest.raises(ValueError):
            normalize_repository(repository(**changes), now)


async def test_import_idempotence_rename_and_native_protection(db, accounts):
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)
    first = normalize_repository(repository(), now)
    assert await store_repository(db, first, now)
    await db.commit()
    original = await db.scalar(select(Project).where(Project.source_external_id == first.external_id))
    original_id, original_slug = original.id, original.slug
    renamed = normalize_repository(repository(full_name="Example/Renamed"), now)
    assert await store_repository(db, renamed, now)
    await db.commit()
    await db.refresh(original)
    assert original.id == original_id and original.slug == original_slug
    assert original.canonical_url == renamed.url
    assert original.stage == "unknown" and original.recruitment_status == "unknown"
    native = Project(
        slug="native-kept", title="Native project", summary="Written by owner",
        description="Owner text", origin="native", owner_id=accounts[0]["id"],
        canonical_url=first.url, visibility="public",
    )
    db.add(native)
    await db.commit()
    assert not await store_repository(db, first, now)
    await db.refresh(native)
    assert native.summary == "Written by owner"


def test_celery_import_can_run_twice_in_separate_event_loops(monkeypatch):
    external_id = str(time_ns())
    now = datetime.now(timezone.utc)
    item = normalize_repository(repository(id=int(external_id)), now)
    monkeypatch.setattr("backend.github_import.fetch_repository", lambda name, checked_at: item)
    monkeypatch.setenv("GITHUB_REPOSITORIES", "example/project")

    try:
        assert import_github.run() == {"imported": 1, "failed": 0, "skipped": 0}
        assert import_github.run() == {"imported": 1, "failed": 0, "skipped": 0}
    finally:
        async def remove_imported_row():
            engine = create_async_engine(ASYNC_DATABASE_URL, poolclass=NullPool)
            try:
                async with async_sessionmaker(engine)() as db:
                    rows = await db.scalars(select(Project).where(Project.source_external_id == external_id))
                    found = rows.all()
                    await db.execute(delete(Project).where(Project.source_external_id == external_id))
                    await db.commit()
                    return len(found)
            finally:
                await engine.dispose()

        assert asyncio.run(remove_imported_row()) == 1
