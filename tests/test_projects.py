from uuid import uuid4

import pytest
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from backend.models import Project, ProjectEngagement

pytestmark = pytest.mark.asyncio


async def create(client, author, **fields):
    body = {"slug": "project-" + uuid4().hex[:12], "title": "Godot project", "summary": "A game prototype",
            "tags": ["Gamedev", "Godot"], "skills": ["Artist"], **fields}
    response = await client.post("/projects", json=body, headers=author["headers"])
    assert response.status_code == 201, response.text
    return response.json()


async def test_project_drafts_and_updates_are_hidden_on_every_old_surface(client, accounts, tmp_path, monkeypatch):
    owner, other = accounts
    project = await create(client, owner)
    slug = project["slug"]
    post = (await client.post("/posts", headers=owner["headers"], json={
        "title": "Godot progress", "content": "Privacy needle", "is_published": True, "project_id": project["id"],
    })).json()
    assert post["project_id"] == project["id"]
    from io import BytesIO
    from PIL import Image
    monkeypatch.setattr("backend.media.MEDIA_ROOT", tmp_path)
    monkeypatch.setattr("backend.routes.media.MEDIA_ROOT", tmp_path)
    buffer = BytesIO()
    Image.new("RGB", (12, 12), "blue").save(buffer, format="PNG")
    assert (await client.put(f"/posts/{post['id']}/image", headers=owner["headers"], content=buffer.getvalue())).status_code == 200
    assert (await client.get(f"/posts/{post['id']}/image", headers=owner["headers"])).status_code == 200
    await client.post("/subscriptions", headers=other["headers"], json={"author_id": owner["id"]})
    for url in (f"/projects/{slug}", f"/projects/{slug}/updates", f"/project/{slug}",
                f"/project/{slug}/updates/{post['id']}", f"/posts/{post['id']}",
                f"/posts/{post['id']}/image", f"/posts/{post['id']}/likes", f"/posts/{post['id']}/comments"):
        assert (await client.get(url)).status_code == 404, url
    for url in ("/explore", "/explore?search=Privacy", f"/authors/{owner['id']}/posts", "/discovery?search=Godot"):
        assert not (await client.get(url)).json()["items"], url
    assert not (await client.get("/feed", headers=other["headers"])).json()["items"]
    assert (await client.get(f"/authors/{owner['id']}")).json()["posts_count"] == 0
    assert (await client.get(f"/posts/{post['id']}", headers=owner["headers"])).status_code == 200
    assert (await client.patch(f"/projects/{slug}", headers=other["headers"], json={"visibility": "public"})).status_code == 404
    assert (await client.post("/posts", headers=other["headers"], json={"content": "No", "project_id": project["id"]})).status_code == 404
    assert (await client.patch(f"/projects/{slug}", headers=owner["headers"], json={"visibility": "public"})).status_code == 200
    assert (await client.get(f"/posts/{post['id']}")).status_code == 200
    assert (await client.get(f"/posts/{post['id']}/image")).status_code == 200
    assert (await client.get(f"/projects/{slug}/updates")).json()["items"][0]["id"] == post["id"]
    assert (await client.delete(f"/users/{owner['id']}", headers=owner["headers"])).status_code == 409
    assert (await client.patch(f"/projects/{slug}", headers=owner["headers"], json={"visibility": "draft"})).status_code == 200
    assert (await client.get(f"/posts/{post['id']}")).status_code == 404
    assert (await client.get(f"/posts/{post['id']}/image")).status_code == 404


async def test_engagement_is_private_until_explicit_consent_and_idempotent(client, accounts, db):
    owner, other = accounts
    project = await create(client, owner, visibility="public")
    base = f"/projects/{project['slug']}"
    assert (await client.get(base + "/engagement")).status_code in (401, 403)
    for _ in range(2):
        response = await client.patch(base + "/engagement", headers=other["headers"],
                                      json={"saved": True, "following": True, "interested": True})
        assert response.status_code == 200, response.text
        assert response.json()["interested_visible"] is False
    assert not (await client.get(base + "/interested")).json()["items"]
    assert await db.scalar(select(func.count()).select_from(ProjectEngagement).where(ProjectEngagement.project_id == project["id"])) == 1
    assert (await client.get("/me/saved-projects", headers=other["headers"])).json()["items"][0]["id"] == project["id"]
    assert (await client.get("/me/followed-projects", headers=other["headers"])).json()["items"][0]["id"] == project["id"]
    await client.patch(base + "/engagement", headers=other["headers"], json={"interested_visible": True})
    users = (await client.get(base + "/interested")).json()["items"]
    assert users[0]["id"] == other["id"] and "email" not in users[0]
    await client.patch(base + "/engagement", headers=other["headers"], json={"interested": False})
    assert not (await client.get(base + "/interested")).json()["items"]
    assert (await client.patch(base + "/engagement", headers=other["headers"], json={"interested_visible": True})).status_code == 422
    state = (await client.get(base + "/engagement", headers=other["headers"])).json()
    assert state == {"saved": True, "following": True, "interested": False, "interested_visible": False}
    assert (await client.patch(base + "/engagement", headers=other["headers"], json={"saved": "true"})).status_code == 422


async def test_discovery_filters_search_cursor_and_safe_public_share(client, accounts):
    owner, _ = accounts
    project = await create(client, owner, visibility="public", description='<script>alert("bad")</script>',
                           source_url="https://github.com/example/project", recruitment_status="open")
    await create(client, owner, visibility="public")
    for query in ("search=Godot", "tag=godot", "skill=artist", "source=native", "recruitment_status=open"):
        assert project["id"] in [item["id"] for item in (await client.get("/discovery?" + query)).json()["items"]]
    assert project["id"] in [item["id"] for item in (await client.get("/discovery?search=artist")).json()["items"]]
    page = (await client.get("/discovery?limit=1")).json()
    assert page["has_more"]
    assert (await client.get("/discovery?limit=1&cursor=" + page["next_cursor"])).json()["items"][0]["id"] != page["items"][0]["id"]
    assert (await client.get("/discovery?tag=other&cursor=" + page["next_cursor"])).status_code == 422
    html = await client.get(f"/project/{project['slug']}")
    assert html.status_code == 200 and 'property="og:title"' in html.text
    assert '<script>alert' not in html.text and '&lt;script&gt;' in html.text
    assert 'rel="canonical"' in html.text
    invalid = await client.post("/projects", headers=owner["headers"], json={
        "slug": "unsafe-url", "title": "Title", "summary": "Summary", "source_url": "javascript:alert(1)"})
    assert invalid.status_code == 422


async def test_project_slug_is_stable_profile_display_name_and_spam_limits(client, accounts, monkeypatch):
    owner, _ = accounts
    project = await create(client, owner)
    assert (await client.patch(f"/projects/{project['slug']}", headers=owner["headers"], json={"slug": "renamed"})).status_code == 422
    response = await client.patch("/me/profile", headers=owner["headers"], json={"display_name": "Creator"})
    assert response.status_code == 200 and response.json()["display_name"] == "Creator"
    assert (await client.get(f"/authors/{owner['id']}")).json()["display_name"] == "Creator"
    monkeypatch.setattr("backend.rate_limit.RATE_LIMIT_PER_MINUTE", 1)
    assert (await client.post("/projects", headers=owner["headers"], json={
        "slug": "another-project", "title": "Title", "summary": "Summary"})).status_code == 429


async def test_database_source_dedup_and_external_owner_optional(db):
    fields = {"title": "Imported", "summary": "From GitHub", "description": "", "origin": "external",
              "visibility": "public", "stage": "unknown", "source_name": "github", "source_external_id": "123"}
    db.add(Project(slug="external-" + uuid4().hex[:12], **fields))
    await db.flush()
    with pytest.raises(IntegrityError):
        async with db.begin_nested():
            db.add(Project(slug="duplicate-" + uuid4().hex[:12], **fields))
            await db.flush()


async def test_drafts_do_not_inflate_project_activity(client, accounts):
    owner, _ = accounts
    project = await create(client, owner, visibility="public")
    timestamp = project["last_activity_at"]
    response = await client.post("/posts", headers=owner["headers"], json={"project_id": project["id"], "content": "Draft"})
    assert response.status_code == 201
    post = response.json()
    assert (await client.get(f"/projects/{project['slug']}")).json()["last_activity_at"] == timestamp
    await client.put(f"/posts/{post['id']}", headers=owner["headers"], json={"content": "Changed draft"})
    assert (await client.get(f"/projects/{project['slug']}")).json()["last_activity_at"] == timestamp
    await client.put(f"/posts/{post['id']}", headers=owner["headers"], json={"is_published": True})
    assert (await client.get(f"/projects/{project['slug']}")).json()["last_activity_at"] > timestamp


async def test_game_dev_alias_and_stale_defaults_preserve_cursor(client, accounts, db):
    from datetime import datetime, timezone
    fields = {"title": "Engine tools", "summary": "A public repository", "description": "", "origin": "external",
              "visibility": "public", "stage": "unknown", "tags": ["game-development"], "skills": [],
              "last_verified_at": datetime.now(timezone.utc), "source_name": "github"}
    ids = []
    for status in ("active", "active", "stale", "archived"):
        project = Project(slug="imported-" + uuid4().hex[:12], status=status, **fields)
        db.add(project)
        await db.flush()
        ids.append(project.id)
    first = (await client.get("/discovery", params={"search": "game dev", "limit": 1})).json()
    assert first["has_more"] and first["items"][0]["id"] in ids[:2]
    second = (await client.get("/discovery", params={"search": "game dev", "limit": 1, "cursor": first["next_cursor"]})).json()
    assert not second["has_more"] and second["items"][0]["id"] in ids[:2]
    assert second["items"][0]["id"] != first["items"][0]["id"]
    for status, expected in (("stale", ids[2]), ("archived", ids[3])):
        page = (await client.get("/discovery", params={"search": "game dev", "status": status})).json()
        assert [project["id"] for project in page["items"]] == [expected]
    assert (await client.get("/discovery", params={"search": "gamedev", "cursor": first["next_cursor"]})).status_code == 422
