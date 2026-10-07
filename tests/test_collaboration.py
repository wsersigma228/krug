from uuid import uuid4
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select, func, update

from backend.models import CollaborationProfile, Project, ProjectApplication, ProjectClaim, ProjectMember, User

pytestmark = pytest.mark.asyncio


async def create_project(client, owner, **fields):
    response = await client.post("/projects", headers=owner["headers"], json={
        "slug": "collab-" + uuid4().hex[:12], "title": "Collaboration project",
        "summary": "A small public project", "visibility": "public", **fields,
    })
    assert response.status_code == 201, response.text
    return response.json()


async def test_profile_discovery_is_opt_in_fresh_and_email_free(client, accounts, db):
    owner, person = accounts
    empty = await client.get("/me/collaboration-profile", headers=person["headers"])
    assert empty.status_code == 200 and empty.json()["discoverable"] is False
    assert await db.scalar(select(func.count()).select_from(CollaborationProfile).where(
        CollaborationProfile.user_id == person["id"])) == 0

    response = await client.put("/me/collaboration-profile", headers=person["headers"], json={
        "skills": ["Python", "python"], "interests": ["Game development"],
        "wanted_skills": ["artist"], "intent_kind": "looking_for_teammates",
        "intent_text": "Looking for a pixel artist", "timezone": "Asia/Tashkent",
        "commitment": "weekends", "discoverable": True, "status": "active",
        "languages": ["en", "ru"], "external_links": ["https://example.com/profile"],
    })
    assert response.status_code == 200, response.text
    found = (await client.get("/people", params={"search": "game dev", "wanted_skill": "artist"})).json()["items"]
    assert len(found) == 1 and found[0]["id"] == person["id"]
    assert found[0]["skills"] == ["python"] and "email" not in found[0]
    assert found[0]["interests"] == ["game development"]
    for alias in ("game dev", "gamedev", "game development", "game-development"):
        people = (await client.get("/people", params={"search": alias, "wanted_skill": "artist"})).json()["items"]
        assert [item["id"] for item in people] == [person["id"]]
    assert (await client.get(f"/people/{person['id']}")).status_code == 200
    assert (await client.get("/people/2147483648")).status_code == 422
    await db.execute(update(CollaborationProfile).where(CollaborationProfile.user_id == person["id"])
                     .values(updated_at=datetime.now(timezone.utc) - timedelta(days=31)))
    await db.commit()
    db.expire_all()
    assert (await client.get("/people", params={"skill": "python"})).json()["items"] == []
    refreshed = await client.put("/me/collaboration-profile", headers=person["headers"], json={
        "skills": ["python"], "interests": ["game-development"], "wanted_skills": ["artist"],
        "intent_kind": "looking_for_teammates", "intent_text": "Looking for a pixel artist",
        "timezone": "Asia/Tashkent", "commitment": "weekends", "discoverable": True,
        "status": "active", "languages": ["en", "ru"], "external_links": ["https://example.com/profile"],
    })
    assert refreshed.status_code == 200
    paused = await client.put("/me/collaboration-profile", headers=person["headers"], json={
        "skills": ["python"], "interests": ["game-development"], "wanted_skills": ["artist"],
        "intent_kind": "looking_for_teammates", "intent_text": "Paused intent",
        "timezone": None, "commitment": None, "discoverable": True,
        "status": "paused", "languages": [], "external_links": [],
    })
    assert paused.status_code == 200
    assert (await client.get(f"/people/{person['id']}")).status_code == 404
    await client.put("/me/collaboration-profile", headers=person["headers"], json={
        "skills": ["python"], "interests": [], "wanted_skills": [],
        "intent_kind": "looking_for_teammates", "intent_text": "Looking for a pixel artist",
        "timezone": "Asia/Tashkent", "commitment": "weekends", "discoverable": True,
        "status": "active", "languages": ["en", "ru"], "external_links": ["https://example.com/profile"],
    })

    private = await client.put("/me/collaboration-profile", headers=person["headers"], json={
        "skills": ["python"], "interests": [], "wanted_skills": [],
        "intent_kind": "looking_for_teammates", "intent_text": "PRIVATE INTENT TOKEN",
        "timezone": None, "commitment": None, "discoverable": False,
        "status": "active", "languages": [], "external_links": [],
    })
    assert private.status_code == 200
    assert (await client.get(f"/people/{person['id']}")).status_code == 404
    share = await client.get(f"/profile/{person['username']}")
    assert share.status_code == 200 and "PRIVATE INTENT TOKEN" not in share.text
    assert (await client.get(f"/authors/{person['id']}")).json()["id"] == person["id"]


async def test_application_acceptance_shares_contacts_and_adds_member_updates(client, accounts, db):
    owner, applicant = accounts
    project = await create_project(client, owner)
    base = f"/projects/{project['slug']}"
    assert (await client.put(base + "/contact-settings", headers=owner["headers"],
                            json={"owner_contact_url": "https://example.com/owner-contact"})).status_code == 204
    assert (await client.get(base + "/contact-settings", headers=applicant["headers"])).status_code == 404
    opening = await client.post(base + "/openings", headers=owner["headers"], json={
        "title": "Python contributor", "role": "Backend developer", "skills": ["Python"],
        "commitment": "part-time", "timezone": "UTC+5", "experience_level": "junior",
        "description": "Help with the API.", "status": "open",
    })
    assert opening.status_code == 201, opening.text
    assert opening.json()["project"] == {"slug": project["slug"], "title": project["title"], "summary": project["summary"]}
    listed = (await client.get("/openings?skill=python")).json()["items"]
    assert listed[0]["project"] == {"slug": project["slug"], "title": project["title"], "summary": project["summary"]}

    apply_url = f"{base}/openings/{opening.json()['id']}/applications"
    payload = {"message": "I can help.", "applicant_contact_url": "https://example.com/applicant-contact"}
    application = await client.post(apply_url, headers=applicant["headers"], json=payload)
    assert application.status_code == 201, application.text
    assert application.json()["status"] == "pending" and application.json()["owner_contact_url"] is None
    assert (await client.post(apply_url, headers=applicant["headers"], json=payload)).status_code == 409
    assert (await client.get(base + "/applications", headers=applicant["headers"])).status_code == 404
    assert (await client.patch(f"{base}/applications/{application.json()['id']}", headers=applicant["headers"],
                               json={"status": "accepted"})).status_code == 404
    owner_view = (await client.get(base + "/applications", headers=owner["headers"])).json()[0]
    assert owner_view["applicant_contact_url"] is None and owner_view["owner_contact_url"] is None

    accepted = await client.patch(f"{base}/applications/{application.json()['id']}",
                                  headers=owner["headers"], json={"status": "accepted"})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["owner_contact_url"] == "https://example.com/owner-contact"
    assert accepted.json()["applicant_contact_url"] == payload["applicant_contact_url"]
    own_application = (await client.get("/me/applications", headers=applicant["headers"])).json()[0]
    assert own_application["project_slug"] == project["slug"]
    assert own_application["owner_contact_url"] == "https://example.com/owner-contact"
    assert await db.scalar(select(func.count()).select_from(ProjectMember).where(
        ProjectMember.project_id == project["id"], ProjectMember.user_id == applicant["id"])) == 1
    assert len((await client.get(base + "/members")).json()["items"]) == 2
    stats = (await client.get(base)).json()
    assert (stats["member_count"], stats["open_roles_count"], stats["interested_count"], stats["published_updates_count"]) == (2, 1, 0, 0)
    share = await client.get(f"/project/{project['slug']}")
    assert all(value in share.text for value in ("Interested people", "Open roles", "Python contributor",
        owner["username"], applicant["username"], "Browse roles", "Find people"))
    assert "owner-contact" not in share.text and "applicant-contact" not in share.text
    await client.patch(base + "/engagement", headers=applicant["headers"], json={"saved": True, "interested": True})
    assert (await client.get(base)).json()["interested_count"] == 0
    await client.patch(base + "/engagement", headers=applicant["headers"], json={"interested_visible": True})
    assert (await client.get(base)).json()["interested_count"] == 1
    assert (await client.delete(f"{base}/openings/{opening.json()['id']}", headers=owner["headers"])).status_code == 409
    assert (await client.post(f"/me/applications/{application.json()['id']}/withdraw",
                              headers=applicant["headers"])).status_code == 409
    repeated = await client.patch(f"{base}/applications/{application.json()['id']}",
                                  headers=owner["headers"], json={"status": "accepted"})
    assert repeated.status_code == 200
    assert await db.scalar(select(func.count()).select_from(ProjectMember).where(
        ProjectMember.project_id == project["id"], ProjectMember.user_id == applicant["id"])) == 1

    owner_update = await client.post("/posts", headers=owner["headers"], json={
        "project_id": project["id"], "title": "Owner update", "content": "Public work", "is_published": True,
    })
    assert owner_update.status_code == 201

    draft = await client.post("/posts", headers=applicant["headers"], json={
        "project_id": project["id"], "title": "Member draft", "content": "Private until published",
    })
    assert draft.status_code == 201, draft.text
    member_updates = (await client.get(base + "/updates", headers=applicant["headers"])).json()["items"]
    assert draft.json()["id"] in [x["id"] for x in member_updates]
    assert [x["id"] for x in (await client.get(base + "/updates")).json()["items"]] == [owner_update.json()["id"]]
    owner_updates = (await client.get(base + "/updates", headers=owner["headers"])).json()["items"]
    assert draft.json()["id"] not in [x["id"] for x in owner_updates]
    published = await client.put(f"/posts/{draft.json()['id']}", headers=applicant["headers"], json={"is_published": True})
    assert published.status_code == 200
    assert (await client.get(base)).json()["published_updates_count"] == 2
    member_page = (await client.get(base + "/updates?limit=1", headers=applicant["headers"])).json()
    assert member_page["has_more"]
    cursor = member_page["next_cursor"]
    assert (await client.get(base + f"/updates?limit=1&cursor={cursor}", headers=owner["headers"])).status_code == 422
    assert (await client.get(base + f"/updates?limit=1&cursor={cursor}")).status_code == 422

    rejected_user = await client.post("/users", json={"username": "reject_" + uuid4().hex[:10], "password": "test-password"})
    assert rejected_user.status_code == 201
    credentials = await client.post("/login", json={"username": rejected_user.json()["username"], "password": "test-password"})
    reject_headers = {"Authorization": f"Bearer {credentials.json()['access_token']}"}
    assert (await client.get(base + "/applications", headers=reject_headers)).status_code == 404
    assert (await client.get(base + "/contact-settings", headers=reject_headers)).status_code == 404
    assert (await client.patch(f"{base}/applications/{application.json()['id']}", headers=reject_headers,
                               json={"status": "rejected"})).status_code == 404
    rejected_app = await client.post(apply_url, headers=reject_headers, json={"message": "Please consider me."})
    assert rejected_app.status_code == 201
    rejected = await client.patch(f"{base}/applications/{rejected_app.json()['id']}",
                                  headers=owner["headers"], json={"status": "rejected"})
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    assert (await client.post(f"/me/applications/{rejected_app.json()['id']}/withdraw",
                              headers=reject_headers)).status_code == 409
    assert not (await client.get(base + "/members")).json()["items"][2:]

    second_opening = await client.post(base + "/openings", headers=owner["headers"], json={
        "title": "Closed role", "role": "Tester", "skills": [], "description": "", "status": "open",
    })
    assert second_opening.status_code == 201
    closed = await client.patch(f"{base}/openings/{second_opening.json()['id']}",
                                headers=owner["headers"], json={"status": "closed"})
    assert closed.status_code == 200
    assert closed.json()["project"]["slug"] == project["slug"]
    assert (await client.post(f"{base}/openings/{second_opening.json()['id']}/applications",
                              headers=reject_headers, json={"message": "Closed role"})).status_code == 404
    assert await db.scalar(select(func.count()).select_from(ProjectApplication).where(
        ProjectApplication.id == application.json()["id"])) == 1


async def test_manual_submission_is_moderated_and_claim_keeps_external_identity(client, accounts, db, monkeypatch):
    submitter, admin = accounts
    response = await client.post("/external-submissions", headers=submitter["headers"], json={
        "title": "Community tool", "summary": "A shared tool", "description": "Review before listing.",
        "tags": ["Tools"], "skills": ["Python"], "source_url": "https://example.com/community-tool",
    })
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "pending"
    assert not (await client.get("/discovery?search=Community")).json()["items"]
    user = await db.get(User, admin["id"])
    user.role = "admin"
    await db.commit()
    queue = (await client.get("/admin/external-submissions", headers=admin["headers"])).json()["items"]
    assert queue[0]["source_url"] == "https://example.com/community-tool"
    reviewed = await client.patch(f"/admin/external-submissions/{response.json()['id']}",
                                  headers=admin["headers"], json={"status": "approved"})
    assert reviewed.status_code == 200, reviewed.text
    external_results = (await client.get("/discovery", params={"source": "external", "search": "Community"})).json()["items"]
    assert [item["slug"] for item in external_results] == [f"manual-project-{response.json()['id']}"]
    project = await db.get(Project, reviewed.json()["project_id"])
    assert project.origin == "external" and project.owner_id is None and project.visibility == "public"
    assert (await client.post(f"/projects/{project.slug}/openings", headers=submitter["headers"], json={
        "title": "Unowned role", "role": "Maintainer", "skills": [], "description": "",
    })).status_code == 404
    derived_response = await client.post("/projects", headers=submitter["headers"], json={
        "slug": "inspired-" + uuid4().hex[:10], "title": "Inspired community tool",
        "summary": "A new project inspired by the listing", "visibility": "public",
        "source_url": project.source_url, "derived_from_project_id": project.id,
    })
    assert derived_response.status_code == 201, derived_response.text
    derived = await db.get(Project, derived_response.json()["id"])
    assert derived.origin == "native" and derived.derived_from_project_id == project.id
    assert derived.canonical_url is None and derived.source_url == project.source_url
    assert project.owner_id is None and project.title == "Community tool"
    invalid_derived = await client.post("/projects", headers=submitter["headers"], json={
        "slug": "overflow-" + uuid4().hex[:10], "title": "Overflow", "summary": "Invalid source id",
        "visibility": "public", "derived_from_project_id": 2_147_483_648,
    })
    assert invalid_derived.status_code == 422
    claim = await client.post(f"/projects/{project.slug}/claims", headers=submitter["headers"], json={
        "evidence_url": "https://example.com/proof"})
    assert claim.status_code == 201, claim.text
    review_claim = await client.patch(f"/admin/project-claims/{claim.json()['id']}",
                                      headers=admin["headers"], json={"status": "approved"})
    assert review_claim.status_code == 200, review_claim.text
    await db.refresh(project)
    assert project.origin == "external" and project.owner_id == submitter["id"]
    assert project.source_name == "manual" and project.source_url == "https://example.com/community-tool"
    claimed_opening = await client.post(f"/projects/{project.slug}/openings", headers=submitter["headers"], json={
        "title": "Maintainer", "role": "Maintainer", "skills": [], "description": "",
    })
    assert claimed_opening.status_code == 201, claimed_opening.text
    assert (await client.patch(f"/projects/{project.slug}", headers=submitter["headers"], json={
        "source_url": "https://example.com/changed"})).status_code == 422

    orphan_submission = await client.post("/external-submissions", headers=submitter["headers"], json={
        "title": "Second community tool", "summary": "Another shared tool", "source_url": "https://example.com/second-tool",
    })
    orphan_review = await client.patch(f"/admin/external-submissions/{orphan_submission.json()['id']}",
                                       headers=admin["headers"], json={"status": "approved"})
    orphan_project = await db.get(Project, orphan_review.json()["project_id"])
    requester = User(username="deleted_claimant_" + uuid4().hex[:10], hashed_password="unused")
    db.add(requester)
    await db.flush()
    orphan_claim = ProjectClaim(project_id=orphan_project.id, requester_id=requester.id,
                               evidence_text="Synthetic evidence for deletion race")
    db.add(orphan_claim)
    await db.flush()
    claim_id, requester_id = orphan_claim.id, requester.id
    original_scalar = db.scalar
    removed = False

    async def delete_requester_after_claim_read(statement, *args, **kwargs):
        nonlocal removed
        result = await original_scalar(statement, *args, **kwargs)
        if not removed and isinstance(result, ProjectClaim):
            removed = True
            await db.execute(delete(User).where(User.id == requester_id))
        return result

    monkeypatch.setattr(db, "scalar", delete_requester_after_claim_read)
    from fastapi import HTTPException
    from backend.project_schemas import ReviewDecision
    from backend.routes.collaboration import review_project_claim
    with pytest.raises(HTTPException) as error:
        await review_project_claim(claim_id, ReviewDecision(status="approved"), db,
                                   await db.get(User, admin["id"]))
    assert error.value.status_code == 404 and removed
    await db.refresh(orphan_project)
    assert orphan_project.owner_id is None


async def test_github_refresh_does_not_replace_claimed_project_copy(db, accounts):
    from backend.github_import import Repository, store_repository
    owner = await db.get(User, accounts[0]["id"])
    project = Project(slug="claimed-" + uuid4().hex[:10], title="Owner-curated title",
        summary="Owner-curated summary", description="Owner-curated details", origin="external",
        status="active", stage="unknown", visibility="public", owner_id=owner.id,
        submitted_by=owner.id, claimed_at=datetime.now(timezone.utc), tags=["curated"], skills=[],
        recruitment_status="unknown", source_name="github", source_url="https://github.com/example/repo",
        canonical_url="https://github.com/example/repo", source_external_id="12345")
    db.add(project)
    await db.flush()
    fresh = Repository("12345", "github-12345", "Upstream title", "Upstream description",
        "https://github.com/example/repo", ["upstream"], ["python"], datetime.now(timezone.utc), "active")
    await store_repository(db, fresh, datetime.now(timezone.utc))
    await db.flush()
    await db.refresh(project)
    assert project.title == "Owner-curated title" and project.summary == "Owner-curated summary"
    assert project.description == "Owner-curated details" and project.tags == ["curated"]


async def test_hidden_and_stale_projects_do_not_accept_applications(client, accounts, db):
    owner, applicant = accounts
    project_data = await create_project(client, owner)
    opening = await client.post(f"/projects/{project_data['slug']}/openings", headers=owner["headers"], json={
        "title": "Hidden role", "role": "Reviewer", "skills": [], "description": "",
    })
    assert opening.status_code == 201
    project = await db.get(Project, project_data["id"])
    project.visibility = "draft"
    await db.commit()
    assert (await client.get(f"/project/{project.slug}")).status_code == 404
    assert (await client.post(f"/projects/{project.slug}/openings/{opening.json()['id']}/applications",
                              headers=applicant["headers"], json={"message": "I can review."})).status_code == 404
    project.visibility = "public"
    project.status = "archived"
    await db.commit()
    assert not (await client.get("/openings?search=Hidden%20role")).json()["items"]
    assert (await client.post(f"/projects/{project.slug}/openings/{opening.json()['id']}/applications",
                              headers=applicant["headers"], json={"message": "I can review."})).status_code == 404
    rejected = await client.post(f"/projects/{project.slug}/openings", headers=owner["headers"], json={
        "title": "Archived role", "role": "Reviewer", "skills": [], "description": "",
    })
    assert rejected.status_code == 422
