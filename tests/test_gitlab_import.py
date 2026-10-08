from datetime import datetime, timezone
from email.message import Message
from urllib.error import HTTPError, URLError

import pytest

from backend.gitlab_import import fetch_project, import_projects, normalize_project
from backend.github_import import store_repository
from backend.models import Project


def project(**changes):
    return {
        "id": 987654321, "name": "Project", "path_with_namespace": "group/subgroup/project",
        "visibility": "public", "description": "A public project", "topics": ["drawing", "drawing"],
        "last_activity_at": "2026-10-01T00:00:00Z", **changes,
    }


def test_normalization_and_public_identity_validation():
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)
    item = normalize_project(project(), now)
    assert item.external_id == "987654321" and item.slug == "gitlab-987654321"
    assert item.url == "https://gitlab.com/group/subgroup/project"
    assert item.tags == ["drawing"] and item.skills == [] and item.status == "active"
    assert normalize_project(project(description=None), now).summary == "group/subgroup/project · GitLab project"
    assert normalize_project(project(archived=True), now).status == "archived"
    assert normalize_project(project(last_activity_at=None), now).status == "stale"
    for changes in (
        {"visibility": "private"}, {"id": True}, {"path_with_namespace": "../other"},
        {"path_with_namespace": "project"}, {"topics": [{}]}, {"last_activity_at": 123},
    ):
        with pytest.raises(ValueError):
            normalize_project(project(**changes), now)


def test_fetch_encodes_path_and_requests_license(monkeypatch):
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, size):
            import json
            return json.dumps(project()).encode()

    class Opener:
        def open(self, request, timeout):
            assert request.full_url == "https://gitlab.com/api/v4/projects/group%2Fsubgroup%2Fproject?license=true"
            assert timeout == 15
            assert "Authorization" not in request.headers
            return Response()

    monkeypatch.setattr("backend.gitlab_import.build_opener", lambda *args: Opener())
    assert fetch_project("group/subgroup/project", datetime.now(timezone.utc)).external_id == "987654321"
    with pytest.raises(ValueError):
        fetch_project("https://example.com/project", datetime.now(timezone.utc))


def test_429_retry_after_is_bounded_and_retried_once(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, size):
            import json
            return json.dumps(project()).encode()

    class Opener:
        attempts = 0
        def open(self, request, timeout):
            self.attempts += 1
            if self.attempts == 1:
                headers = Message()
                headers["Retry-After"] = "30"
                raise HTTPError(request.full_url, 429, "limited", headers, None)
            return Response()

    opener = Opener()
    delays = []
    monkeypatch.setattr("backend.gitlab_import.build_opener", lambda *args: opener)
    monkeypatch.setattr("backend.gitlab_import.sleep", delays.append)
    fetch_project("group/project", datetime.now(timezone.utc))
    assert delays == [30] and opener.attempts == 2


def test_long_retry_after_is_not_retried_early(monkeypatch):
    class Opener:
        attempts = 0
        def open(self, request, timeout):
            self.attempts += 1
            headers = Message()
            headers["Retry-After"] = "60"
            raise HTTPError(request.full_url, 429, "limited", headers, None)

    opener = Opener()
    delays = []
    monkeypatch.setattr("backend.gitlab_import.build_opener", lambda *args: opener)
    monkeypatch.setattr("backend.gitlab_import.sleep", delays.append)
    with pytest.raises(HTTPError):
        fetch_project("group/project", datetime.now(timezone.utc))
    assert delays == [] and opener.attempts == 1


def test_network_failure_is_not_treated_as_project_metadata(monkeypatch):
    def fail(*args, **kwargs):
        raise URLError("offline")
    monkeypatch.setattr("backend.gitlab_import.build_opener", lambda *args: type("Opener", (), {"open": fail})())
    with pytest.raises(URLError):
        fetch_project("group/project", datetime.now(timezone.utc))


@pytest.mark.asyncio
async def test_import_limit_checked_before_database_access():
    with pytest.raises(ValueError, match="at most 10"):
        await import_projects(None, ["group/project"] * 11)


@pytest.mark.asyncio
async def test_gitlab_lock_is_independent_and_rejects_overlapping_gitlab_run():
    class LockDB:
        held = {(731945, 1)}  # Simulates an active GitHub import.

        async def scalar(self, statement):
            assert str(statement) == "SELECT pg_try_advisory_xact_lock(731945, 2)"
            key = (731945, 2)
            if key in self.held:
                return False
            self.held.add(key)
            return True

        async def execute(self, statement):
            pass

        async def commit(self):
            pass

    db = LockDB()
    assert await import_projects(db, []) == {"imported": 0, "failed": 0, "skipped": 0}
    assert await import_projects(db, []) == {"imported": 0, "failed": 0, "skipped": 0, "busy": True}


@pytest.mark.asyncio
async def test_store_uses_gitlab_source_and_preserves_claimed_project(db, accounts):
    now = datetime(2026, 10, 6, tzinfo=timezone.utc)
    claimed = Project(
        slug="claimed-project", title="Owner title", summary="Owner summary", description="Owner description",
        origin="external", status="paused", stage="building", visibility="public", owner_id=accounts[0]["id"],
        claimed_at=now, source_name="gitlab", source_url="https://gitlab.com/group/subgroup/project",
        source_external_id="987654321", canonical_url="https://gitlab.com/group/subgroup/project",
        recruitment_status="closed",
    )
    db.add(claimed)
    await db.flush()
    item = normalize_project(project(), now)
    assert await store_repository(db, item, now, source_name="gitlab")
    await db.flush()
    await db.refresh(claimed)
    assert claimed.source_name == "gitlab"
    assert (claimed.title, claimed.summary, claimed.stage, claimed.status, claimed.recruitment_status) == (
        "Owner title", "Owner summary", "building", "paused", "closed",
    )
