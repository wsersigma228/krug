from datetime import datetime, timedelta, timezone
import asyncio
import os
from io import BytesIO
from uuid import uuid4

import pytest
from pydantic import ValidationError
from PIL import Image
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.database import get_db
from backend.main import api
from backend.models import Comment, Like, Post, Team, TeamApplication, TeamMember, TeamOpening, User
from backend.platform_schemas import EventInput
from backend.security import create_access_token


def slug(prefix):
    return f"{prefix}-{uuid4().hex[:12]}"


def event_body(event_slug=None, **changes):
    now = datetime.now(timezone.utc)
    body = {
        "slug": event_slug or slug("jam"),
        "title": "Community game jam",
        "summary": "Make a small game together",
        "type": "game_jam",
        "starts_at": (now + timedelta(days=1)).isoformat(),
        "ends_at": (now + timedelta(days=3)).isoformat(),
        "deadline": (now + timedelta(days=2)).isoformat(),
        "timezone": "Asia/Tashkent",
        "visibility": "public",
        "status": "scheduled",
    }
    body.update(changes)
    return body


async def test_team_application_acceptance_and_project_transfer(client, accounts):
    owner, applicant = accounts
    host_event = await client.post("/events", headers=owner["headers"], json=event_body())
    assert host_event.status_code == 201, host_event.text
    team_slug = slug("team")
    created = await client.post("/teams", headers=owner["headers"], json={
        "slug": team_slug, "title": "Game team", "summary": "Looking for artists",
        "visibility": "public", "skills": ["art"], "languages": ["en"],
        "event_id": host_event.json()["id"],
    })
    assert created.status_code == 201, created.text
    assert created.json()["is_member"] is True
    assert [row["id"] for row in (await client.get(f"/teams?event_id={host_event.json()['id']}")).json()["items"]] == [created.json()["id"]]
    opening = await client.post(f"/teams/{team_slug}/openings", headers=owner["headers"], json={
        "title": "Artist", "role": "2D artist", "skills": ["art"],
        "description": "Create character concepts",
    })
    assert opening.status_code == 201, opening.text
    response = await client.post(f"/team-openings/{opening.json()['id']}/applications",
                                 headers=applicant["headers"], json={"message": "I can help"})
    assert response.status_code == 201, response.text
    application_id = response.json()["id"]
    duplicate = await client.post(f"/team-openings/{opening.json()['id']}/applications",
                                  headers=applicant["headers"], json={"message": "Again"})
    assert duplicate.status_code == 409
    accepted = await client.patch(f"/team-applications/{application_id}", headers=owner["headers"],
                                  json={"status": "accepted"})
    assert accepted.status_code == 200 and accepted.json()["status"] == "accepted"
    members = (await client.get(f"/teams/{team_slug}/members")).json()["items"]
    assert {member["user_id"] for member in members} == {owner["id"], applicant["id"]}
    assert all("avatar_key" not in member for member in members)
    project = await client.post(f"/teams/{team_slug}/project", headers=owner["headers"], json={
        "slug": slug("project"), "title": "The jam game", "summary": "Our game",
        "visibility": "public", "languages": ["en"], "format": "hybrid",
    })
    assert project.status_code == 201, project.text
    assert project.json()["format"] == "hybrid"
    filtered = (await client.get("/discovery", params={"format": "hybrid"})).json()["items"]
    assert any(row["id"] == project.json()["id"] for row in filtered)
    assert (await client.get(f"/teams/{team_slug}")).json()["linked_project_id"] == project.json()["id"]
    assert (await client.get(f"/projects/{project.json()['slug']}/members")).json()["items"]


async def test_platform_search_matches_skill_and_topic_labels(client, accounts):
    owner, _ = accounts
    topic = "game-development"
    team = await client.post("/teams", headers=owner["headers"], json={
        "slug": slug("tag-team"), "title": "A team", "summary": "Just a team",
        "visibility": "public", "topics": [topic],
    })
    community = await client.post("/communities", headers=owner["headers"], json={
        "slug": slug("tag-community"), "title": "A community", "summary": "Just a community",
        "visibility": "public", "skills": [topic],
    })
    event = await client.post("/events", headers=owner["headers"], json=event_body(
        slug("tag-event"), title="A jam", summary="Just a jam", skills=[topic]))
    assert team.status_code == community.status_code == event.status_code == 201

    for path, expected in (("/teams", team.json()), ("/communities", community.json()), ("/events", event.json())):
        result = await client.get(path, params={"search": "game dev"})
        assert result.status_code == 200, result.text
        assert [item["id"] for item in result.json()["items"]] == [expected["id"]]


async def test_platform_entity_create_rate_limit_runs_before_row_locks(client, accounts, monkeypatch):
    owner, _ = accounts
    monkeypatch.setattr("backend.rate_limit.RATE_LIMIT_PER_MINUTE", 1)
    def payload(prefix):
        return {"slug": slug(prefix), "title": "Rate limited entity", "summary": "Created once",
                "visibility": "public"}

    for path, body in (
        ("/teams", payload("limited-team")),
        ("/communities", payload("limited-community")),
        ("/events", event_body(slug("limited-event"))),
    ):
        first = await client.post(path, headers=owner["headers"], json=body)
        second_body = body | {"slug": slug("limited-again")}
        second = await client.post(path, headers=owner["headers"], json=second_body)
        assert first.status_code == 201, first.text
        assert second.status_code == 429, second.text


async def test_team_application_rate_limit(client, accounts, monkeypatch):
    owner, applicant = accounts
    team_slug = slug("limited-app-team")
    team = await client.post("/teams", headers=owner["headers"], json={
        "slug": team_slug, "title": "Apply once", "summary": "Rate limited applications",
        "visibility": "public",
    })
    assert team.status_code == 201, team.text
    opening = await client.post(f"/teams/{team_slug}/openings", headers=owner["headers"], json={
        "title": "Role", "role": "Contributor",
    })
    assert opening.status_code == 201, opening.text
    monkeypatch.setattr("backend.rate_limit.RATE_LIMIT_PER_MINUTE", 1)
    url = f"/team-openings/{opening.json()['id']}/applications"
    first = await client.post(url, headers=applicant["headers"], json={"message": "Interested"})
    second = await client.post(url, headers=applicant["headers"], json={"message": "Try again"})
    assert first.status_code == 201 and second.status_code == 429


async def test_team_transfer_shares_project_create_rate_limit(client, accounts, monkeypatch):
    owner, _ = accounts
    monkeypatch.setattr("backend.rate_limit.RATE_LIMIT_PER_MINUTE", 1)
    ordinary = await client.post("/projects", headers=owner["headers"], json={
        "slug": slug("ordinary-before-transfer"), "title": "Ordinary", "summary": "Uses project budget",
    })
    assert ordinary.status_code == 201, ordinary.text
    team_slug = slug("limited-transfer")
    team = await client.post("/teams", headers=owner["headers"], json={
        "slug": team_slug, "title": "Transfer", "summary": "Shares project creation budget",
    })
    assert team.status_code == 201, team.text
    transfer = await client.post(f"/teams/{team_slug}/project", headers=owner["headers"], json={
        "slug": slug("project-transfer"), "title": "Transferred", "summary": "Also project creation",
    })
    assert transfer.status_code == 429


async def test_new_entity_engagement_rate_limits(client, accounts, monkeypatch):
    owner, _ = accounts
    team_slug = slug("engagement-team")
    community_slug = slug("engagement-community")
    event_slug = slug("engagement-event")
    team = await client.post("/teams", headers=owner["headers"], json={
        "slug": team_slug, "title": "Team", "summary": "Engagement limit",
    })
    community = await client.post("/communities", headers=owner["headers"], json={
        "slug": community_slug, "title": "Community", "summary": "Engagement limit",
    })
    event = await client.post("/events", headers=owner["headers"], json=event_body(event_slug))
    assert team.status_code == community.status_code == event.status_code == 201
    monkeypatch.setattr("backend.rate_limit.RATE_LIMIT_PER_MINUTE", 1)
    for path in (f"/teams/{team_slug}/engagement", f"/communities/{community_slug}/engagement",
                 f"/events/{event_slug}/engagement"):
        first = await client.patch(path, headers=owner["headers"], json={"saved": True})
        second = await client.patch(path, headers=owner["headers"], json={"saved": False})
        assert first.status_code == 200, first.text
        assert second.status_code == 429, second.text


async def test_community_membership_post_visibility_moderation_and_owner_guard(client, accounts):
    owner, member = accounts
    community_slug = slug("community")
    created = await client.post("/communities", headers=owner["headers"], json={
        "slug": community_slug, "title": "Pixel artists", "summary": "Share game art",
        "visibility": "public", "topics": ["pixel art"],
    })
    assert created.status_code == 201, created.text
    assert (await client.delete(f"/communities/{community_slug}/membership", headers=owner["headers"])).status_code == 409
    for publish in (False, True):
        rejected = await client.post("/posts", headers=member["headers"], json={
            "title": "Not a member", "content": "Join first", "community_id": created.json()["id"],
            "is_published": publish,
        })
        assert rejected.status_code == 403
    assert (await client.put(f"/communities/{community_slug}/membership", headers=member["headers"])).status_code == 204
    assert (await client.get(f"/communities/{community_slug}/membership", headers=member["headers"])).json() == {
        "is_member": True, "is_owner": False,
    }
    post = await client.post("/posts", headers=member["headers"], json={
        "title": "Sketches", "content": "Drawing sprites", "community_id": created.json()["id"],
        "is_published": True,
    })
    assert post.status_code == 201, post.text
    assert post.json()["community_id"] == created.json()["id"]
    post_id = post.json()["id"]
    assert (await client.get(f"/posts/{post_id}")).status_code == 200
    comment = await client.post(f"/posts/{post_id}/comments", headers=owner["headers"],
                                json={"content": "Helpful community feedback"})
    assert comment.status_code == 201
    assert (await client.delete(f"/posts/{post_id}/comments/{comment.json()['id']}",
                                headers=member["headers"])).status_code == 204
    community_owner_moderated = await client.post(f"/posts/{post_id}/comments", headers=member["headers"],
                                                   json={"content": "Member follow-up"})
    assert community_owner_moderated.status_code == 201
    assert (await client.put(f"/posts/{post.json()['id']}", headers=member["headers"], json={
        "community_id": None, "content": "move outside community",
    })).status_code == 422
    assert (await client.delete(f"/communities/{community_slug}/membership",
                                headers=member["headers"])).status_code == 204
    assert (await client.put(f"/posts/{post_id}", headers=member["headers"],
                             json={"content": "I left"})).status_code == 403
    assert (await client.patch(f"/communities/{community_slug}", headers=owner["headers"],
                               json={"visibility": "draft"})).status_code == 200
    for url in (f"/posts/{post_id}", f"/posts/{post_id}/likes", f"/posts/{post_id}/comments"):
        assert (await client.get(url)).status_code == 404
    assert (await client.delete(f"/posts/{post_id}/comments/{community_owner_moderated.json()['id']}",
                                headers=owner["headers"])).status_code == 204
    for url in ("/explore?search=Drawing", f"/authors/{member['id']}/posts"):
        assert not (await client.get(url)).json()["items"]
    assert (await client.get(f"/posts/{post_id}", headers=member["headers"])).status_code == 200
    assert (await client.delete(f"/posts/{post_id}", headers=owner["headers"])).status_code == 204


async def test_deleting_community_flushes_posts_before_restricted_entity(client, accounts, db, tmp_path, monkeypatch):
    owner, member = accounts
    monkeypatch.setattr("backend.media.MEDIA_ROOT", tmp_path)
    monkeypatch.setattr("backend.routes.media.MEDIA_ROOT", tmp_path)
    community_slug = slug("delete-community")
    created = await client.post("/communities", headers=owner["headers"], json={
        "slug": community_slug, "title": "Delete test", "summary": "Remove owned posts before community",
        "visibility": "public",
    })
    assert created.status_code == 201, created.text
    community_id = created.json()["id"]
    assert (await client.put(f"/communities/{community_slug}/membership", headers=member["headers"])).status_code == 204

    published = await client.post("/posts", headers=member["headers"], json={
        "community_id": community_id, "title": "Published", "content": "Community content", "is_published": True,
    })
    draft = await client.post("/posts", headers=member["headers"], json={
        "community_id": community_id, "title": "Draft", "content": "Private community draft",
    })
    unrelated = await client.post("/posts", headers=owner["headers"], json={
        "title": "Unrelated", "content": "Keep this standalone post", "is_published": True,
    })
    assert published.status_code == draft.status_code == unrelated.status_code == 201
    published_id, draft_id, unrelated_id = published.json()["id"], draft.json()["id"], unrelated.json()["id"]

    image = BytesIO()
    Image.new("RGB", (20, 20), "green").save(image, format="PNG")
    uploaded = await client.put(f"/posts/{published_id}/image", headers=member["headers"], content=image.getvalue())
    assert uploaded.status_code == 200, uploaded.text
    image_files = set(tmp_path.iterdir())
    assert image_files
    liked = await client.put(f"/posts/{published_id}/likes", headers=owner["headers"])
    comment = await client.post(f"/posts/{published_id}/comments", headers=owner["headers"],
                                json={"content": "Community comment"})
    assert liked.status_code == 200 and comment.status_code == 201

    deleted = await client.delete(f"/communities/{community_slug}", headers=owner["headers"])
    assert deleted.status_code == 204, deleted.text
    assert (await client.get(f"/communities/{community_slug}")).status_code == 404
    assert await db.get(Post, published_id) is None
    assert await db.get(Post, draft_id) is None
    assert await db.get(Comment, comment.json()["id"]) is None
    assert await db.scalar(select(func.count()).select_from(Like).where(Like.post_id == published_id)) == 0
    assert await db.get(Post, unrelated_id) is not None
    assert not any(path.exists() for path in image_files)


async def test_event_validation_visibility_engagement_and_saved_filters(client, accounts):
    owner, viewer = accounts
    body = event_body()
    # The submission deadline may fall during a multi-day event.
    from backend.platform_schemas import EventInput
    parsed = EventInput.model_validate(body)
    assert parsed.deadline > parsed.starts_at
    with pytest.raises(ValidationError):
        EventInput.model_validate(event_body(deadline=(datetime.now(timezone.utc) + timedelta(days=4)).isoformat()))
    with pytest.raises(ValidationError):
        EventInput.model_validate(event_body(timezone="Mars/Olympus"))
    with pytest.raises(ValidationError):
        EventInput.model_validate(event_body(origin="external", source_external_id="claimed-id"))

    body.update(origin="external", source_name="Local game jam list",
                source_url="https://events.example.test/jams/one/?ref=krug#details")
    created = await client.post("/events", headers=owner["headers"], json=body)
    assert created.status_code == 201, created.text
    assert created.json()["origin"] == "external"
    assert created.json()["owner_id"] == owner["id"]
    assert created.json()["source_name"] == "Local game jam list"
    assert created.json()["canonical_url"] == "https://events.example.test/jams/one?ref=krug"
    duplicate = await client.post("/events", headers=owner["headers"], json=event_body(
        slug("duplicate-source")))
    assert duplicate.status_code == 201
    conflict = await client.patch(f"/events/{duplicate.json()['slug']}", headers=owner["headers"], json={
        "source_url": body["source_url"],
    })
    assert conflict.status_code == 409
    unchanged = await client.get(f"/events/{duplicate.json()['slug']}", headers=owner["headers"])
    assert unchanged.status_code == 200 and unchanged.json()["source_url"] is None
    slug_name = created.json()["slug"]
    engagement = await client.patch(f"/events/{slug_name}/engagement", headers=viewer["headers"],
                                    json={"saved": True, "interested": True})
    assert engagement.status_code == 200, engagement.text
    assert engagement.json()["saved"] is True and engagement.json()["interested"] is True
    visible_interest = await client.patch(f"/events/{slug_name}/engagement", headers=viewer["headers"],
                                          json={"interested_visible": True})
    assert visible_interest.status_code == 200 and visible_interest.json()["interested_visible"] is True
    interested_people = await client.get(f"/events/{slug_name}/interested")
    assert interested_people.json()["items"][0]["id"] == viewer["id"]
    assert "avatar_key" not in interested_people.json()["items"][0]
    filtered = await client.get("/events?saved=true", headers=viewer["headers"])
    assert [row["id"] for row in filtered.json()["items"]] == [created.json()["id"]]
    assert (await client.get("/events?saved=true")).status_code == 401
    hidden = await client.post("/events", headers=owner["headers"], json=event_body(
        visibility="draft", slug=slug("private")))
    assert hidden.status_code == 201
    assert (await client.get(f"/events/{hidden.json()['slug']}")).status_code == 404


async def test_team_search_and_private_cursor_scope(client, accounts):
    owner, other = accounts
    private = await client.post("/teams", headers=owner["headers"], json={
        "slug": slug("private-team"), "title": "Private Artist Workshop", "summary": "Invite only",
    })
    public = await client.post("/teams", headers=owner["headers"], json={
        "slug": slug("public-team"), "title": "Public Artist Workshop", "summary": "Open to all",
        "visibility": "public",
    })
    assert private.status_code == public.status_code == 201
    owner_page = await client.get("/teams?search=Artist&limit=1", headers=owner["headers"])
    assert owner_page.status_code == 200
    if owner_page.json()["has_more"]:
        other_page = await client.get("/teams?search=Artist&limit=1&cursor=" +
                                      owner_page.json()["next_cursor"], headers=other["headers"])
        assert other_page.status_code == 422
    guest = await client.get("/teams?search=Artist")
    assert private.json()["id"] not in [row["id"] for row in guest.json()["items"]]
    assert public.json()["id"] in [row["id"] for row in guest.json()["items"]]


async def test_event_patch_revalidates_deadline_against_merged_state(client, accounts):
    owner, _ = accounts
    body = event_body()
    created = await client.post("/events", headers=owner["headers"], json=body)
    assert created.status_code == 201, created.text
    invalid = await client.patch(f"/events/{created.json()['slug']}", headers=owner["headers"], json={
        "deadline": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
    })
    assert invalid.status_code == 422
    valid = await client.patch(f"/events/{created.json()['slug']}", headers=owner["headers"], json={
        "deadline": (datetime.now(timezone.utc) + timedelta(days=2, hours=12)).isoformat(),
    })
    assert valid.status_code == 200, valid.text


async def test_event_list_date_filters_are_cursor_serializable(client, accounts):
    owner, _ = accounts
    start = datetime.now(timezone.utc) + timedelta(days=4)
    first = await client.post("/events", headers=owner["headers"], json=event_body(
        slug("bounded-a"), starts_at=start.isoformat(), ends_at=(start + timedelta(days=1)).isoformat(),
        deadline=None))
    second = await client.post("/events", headers=owner["headers"], json=event_body(
        slug("bounded-b"), starts_at=(start + timedelta(hours=1)).isoformat(),
        ends_at=(start + timedelta(days=1, hours=1)).isoformat(), deadline=None))
    assert first.status_code == second.status_code == 201
    filters = {"starts_after": (start - timedelta(minutes=1)).isoformat(),
               "starts_before": (start + timedelta(days=2)).isoformat(), "limit": 1}
    page = await client.get("/events", params=filters)
    assert page.status_code == 200, page.text
    assert page.json()["has_more"] is True
    next_page = await client.get("/events", params={**filters, "cursor": page.json()["next_cursor"]})
    assert next_page.status_code == 200, next_page.text
    assert [page.json()["items"][0]["id"], next_page.json()["items"][0]["id"]] == [
        second.json()["id"], first.json()["id"],
    ]
    wrong_filter = await client.get("/events", params={
        **filters, "starts_before": (start + timedelta(days=3)).isoformat(),
        "cursor": page.json()["next_cursor"],
    })
    assert wrong_filter.status_code == 422


async def test_upcoming_events_order_excludes_ended_cancelled_and_pages(client, accounts):
    owner, _ = accounts
    start = datetime.now(timezone.utc) + timedelta(days=5)
    later = await client.post("/events", headers=owner["headers"], json=event_body(
        slug("later"), starts_at=(start + timedelta(days=1)).isoformat(),
        ends_at=(start + timedelta(days=2)).isoformat(), deadline=None))
    earlier = await client.post("/events", headers=owner["headers"], json=event_body(
        slug("earlier"), starts_at=start.isoformat(), ends_at=(start + timedelta(days=1)).isoformat(),
        deadline=None))
    cancelled = await client.post("/events", headers=owner["headers"], json=event_body(
        slug("cancelled"), status="cancelled", starts_at=start.isoformat(),
        ends_at=(start + timedelta(days=1)).isoformat(), deadline=None))
    ended = await client.post("/events", headers=owner["headers"], json=event_body(
        slug("ended"), status="ended", starts_at=start.isoformat(),
        ends_at=(start + timedelta(days=1)).isoformat(), deadline=None))
    assert all(response.status_code == 201 for response in (later, earlier, cancelled, ended))
    page = await client.get("/events?upcoming=true&limit=1")
    assert page.status_code == 200
    assert page.json()["items"][0]["id"] == earlier.json()["id"]
    assert page.json()["has_more"] is True
    next_page = await client.get("/events?upcoming=true&limit=1&cursor=" + page.json()["next_cursor"])
    assert next_page.status_code == 200
    assert next_page.json()["items"][0]["id"] == later.json()["id"]
    all_upcoming = [row["id"] for row in (await client.get("/events?upcoming=true")).json()["items"]]
    assert cancelled.json()["id"] not in all_upcoming
    assert ended.json()["id"] not in all_upcoming


async def test_covers_and_avatars_are_real_private_and_replacement_is_safe(
        client, accounts, tmp_path, monkeypatch):
    owner, other = accounts
    monkeypatch.setattr("backend.media.MEDIA_ROOT", tmp_path)
    monkeypatch.setattr("backend.routes.media.MEDIA_ROOT", tmp_path)
    buffer = BytesIO()
    Image.new("RGB", (20, 20), "blue").save(buffer, format="PNG")
    image = buffer.getvalue()
    team = await client.post("/teams", headers=owner["headers"], json={
        "slug": slug("covered"), "title": "Private team", "summary": "Not listed",
    })
    assert team.status_code == 201
    cover = await client.put(f"/teams/{team.json()['slug']}/cover", headers=owner["headers"], content=image)
    assert cover.status_code == 200 and cover.json()["cover_url"].endswith("/cover")
    original = set(tmp_path.iterdir())
    assert (await client.get(cover.json()["cover_url"], headers=owner["headers"])).status_code == 200
    assert (await client.get(cover.json()["cover_url"])).status_code == 404
    assert (await client.get(cover.json()["cover_url"], headers=other["headers"])).status_code == 404
    invalid = await client.put(f"/teams/{team.json()['slug']}/cover", headers=owner["headers"], content=b"not an image")
    assert invalid.status_code == 422
    assert set(tmp_path.iterdir()) == original
    assert (await client.get(cover.json()["cover_url"], headers=owner["headers"])).status_code == 200

    avatar = await client.put("/me/avatar", headers=owner["headers"], content=image)
    assert avatar.status_code == 200 and avatar.json()["avatar_url"] == f"/users/{owner['id']}/avatar"
    public_avatar = await client.get(avatar.json()["avatar_url"])
    assert public_avatar.status_code == 200 and public_avatar.headers["content-type"] == "image/jpeg"
    assert (await client.get(f"/teams/{team.json()['slug']}/members")).status_code == 404
    members_response = await client.get(f"/teams/{team.json()['slug']}/members", headers=owner["headers"])
    assert members_response.status_code == 200
    members = members_response.json()["items"]
    assert next(row for row in members if row["user_id"] == owner["id"])["avatar_url"] == avatar.json()["avatar_url"]
    assert "avatar_key" not in (await client.get(f"/teams/{team.json()['slug']}")).text
    assert (await client.delete("/me/avatar", headers=owner["headers"])).status_code == 204
    assert (await client.get(avatar.json()["avatar_url"])).status_code == 404


async def test_concurrent_acceptance_uses_independent_sessions():
    database_url = os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://myuser:1234@localhost:5432/test_db")
    engine = create_async_engine(database_url.replace(
        "postgresql+psycopg://", "postgresql+psycopg_async://"), poolclass=NullPool)
    suffix = uuid4().hex[:12]
    owner = User(username=f"accept_owner_{suffix}", hashed_password="unused", role="user")
    applicant = User(username=f"accept_applicant_{suffix}", hashed_password="unused", role="user")
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add_all([owner, applicant])
        await session.flush()
        team = Team(slug=f"accept-team-{suffix}", title="Acceptance", summary="Concurrency test",
                    owner_id=owner.id, visibility="public", status="recruiting")
        session.add(team)
        await session.flush()
        session.add(TeamMember(team_id=team.id, user_id=owner.id, role="Owner"))
        opening = TeamOpening(team_id=team.id, title="Tester", role="Tester", status="open")
        session.add(opening)
        await session.flush()
        application = TeamApplication(opening_id=opening.id, applicant_id=applicant.id,
                                      message="Please accept")
        session.add(application)
        await session.commit()
        team_slug, application_id = team.slug, application.id
        headers = {"Authorization": "Bearer " + create_access_token({
            "sub": owner.username, "user_id": owner.id, "version": owner.token_version,
        })}
        owner_id, applicant_id = owner.id, applicant.id

    async def request_db():
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    api.dependency_overrides[get_db] = request_db
    try:
        async with (AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as first,
                    AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as second):
            results = await asyncio.gather(*[
                first.patch(f"/team-applications/{application_id}", headers=headers,
                            json={"status": "accepted"}),
                second.patch(f"/team-applications/{application_id}", headers=headers,
                             json={"status": "accepted"}),
            ])
            assert sorted(response.status_code for response in results) == [200, 409]
        async with AsyncSession(engine, expire_on_commit=False) as session:
            assert await session.scalar(select(TeamApplication.status).where(
                TeamApplication.id == application_id)) == "accepted"
            assert await session.scalar(select(TeamMember.id).where(
                TeamMember.team_id == team.id, TeamMember.user_id == applicant_id)) is not None
    finally:
        api.dependency_overrides.clear()
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await session.execute(delete(Team).where(Team.slug == team_slug))
            await session.execute(delete(User).where(User.id.in_([owner_id, applicant_id])))
            await session.commit()
        await engine.dispose()


async def test_apply_waits_for_concurrent_opening_close_then_rejects():
    database_url = os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://myuser:1234@localhost:5432/test_db")
    engine = create_async_engine(database_url.replace(
        "postgresql+psycopg://", "postgresql+psycopg_async://"), poolclass=NullPool)
    suffix = uuid4().hex[:12]
    owner = User(username=f"close_owner_{suffix}", hashed_password="unused", role="user")
    applicant = User(username=f"close_applicant_{suffix}", hashed_password="unused", role="user")
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add_all([owner, applicant])
        await session.flush()
        team = Team(slug=f"close-team-{suffix}", title="Closing", summary="Race test",
                    owner_id=owner.id, visibility="public", status="recruiting")
        session.add(team)
        await session.flush()
        session.add(TeamMember(team_id=team.id, user_id=owner.id, role="Owner"))
        opening = TeamOpening(team_id=team.id, title="Artist", role="Artist", status="open")
        session.add(opening)
        await session.commit()
        team_slug, opening_id = team.slug, opening.id
        owner_id, applicant_id = owner.id, applicant.id
        headers = {"Authorization": "Bearer " + create_access_token({
            "sub": applicant.username, "user_id": applicant.id, "version": applicant.token_version,
        })}

    close_session = AsyncSession(engine, expire_on_commit=False)
    locked_team = await close_session.scalar(select(Team).where(Team.slug == team_slug).with_for_update())
    locked_opening = await close_session.scalar(select(TeamOpening).where(
        TeamOpening.id == opening_id).with_for_update())
    assert locked_team is not None and locked_opening is not None
    locked_opening.status = "closed"
    await close_session.flush()

    request_started = asyncio.Event()

    async def request_db():
        async with AsyncSession(engine, expire_on_commit=False) as session:
            request_started.set()
            yield session

    api.dependency_overrides[get_db] = request_db
    try:
        async with AsyncClient(transport=ASGITransport(app=api), base_url="http://test") as client:
            request = asyncio.create_task(client.post(
                f"/team-openings/{opening_id}/applications", headers=headers,
                json={"message": "Please consider me"}))
            await asyncio.wait_for(request_started.wait(), timeout=5)
            await asyncio.sleep(0.1)
            assert not request.done(), "application should wait on the locked team row"
            await close_session.commit()
            response = await request
            assert response.status_code == 404, response.text
        async with AsyncSession(engine, expire_on_commit=False) as session:
            assert await session.scalar(select(TeamApplication.id).where(
                TeamApplication.opening_id == opening_id)) is None
    finally:
        api.dependency_overrides.clear()
        await close_session.close()
        async with AsyncSession(engine, expire_on_commit=False) as session:
            await session.execute(delete(Team).where(Team.slug == team_slug))
            await session.execute(delete(User).where(User.id.in_([owner_id, applicant_id])))
            await session.commit()
        await engine.dispose()
