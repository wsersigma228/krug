from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi.responses import HTMLResponse
from html import escape

from backend.database import get_db
from backend.models import (CollaborationProfile, ExternalSubmission, Project, ProjectApplication,
                            ProjectClaim, ProjectMember, ProjectOpening, User)
from backend.pagination import cursor_scope, decode_cursor, encode_cursor, make_page, seek_page
from backend.project_schemas import (ApplicationCreate, ApplicationStatus, ClaimInput, CollaborationProfileInput,
    CollaborationProfileResponse, ContactSettings, ExternalSubmissionInput, OpeningInput, OpeningPatch, OpeningResponse,
    OpeningSearchParams, PeopleParams, ProjectApplicationResponse, PublicPerson, ReviewDecision)
from backend.schemas import Page, PageParams
from backend.security import get_current_admin, get_current_user, get_optional_user
from backend.rate_limit import check_rate_limit
from backend.project_access import canonical_project_url
from backend.routes.projects import get_project, public_page

router = APIRouter()
DatabaseId = Annotated[int, Path(gt=0, le=2_147_483_647)]


def discoverable_profile():
    fresh_since = datetime.now(timezone.utc) - timedelta(days=30)
    return (CollaborationProfile.discoverable.is_(True), CollaborationProfile.status == "active",
            CollaborationProfile.intent_kind.is_not(None), CollaborationProfile.updated_at >= fresh_since)


def person_data(user, profile, owned, memberships):
    return {"id": user.id, "username": user.username, "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "bio": user.bio, "skills": profile.skills, "interests": profile.interests,
            "wanted_skills": profile.wanted_skills, "intent_kind": profile.intent_kind,
            "intent_text": profile.intent_text, "timezone": profile.timezone,
            "commitment": profile.commitment, "languages": profile.languages,
            "external_links": profile.external_links, "updated_at": profile.updated_at,
            "owned_projects": owned, "memberships": memberships}


async def public_projects(db, user_id):
    rows = (await db.execute(select(Project, ProjectMember.role).outerjoin(
        ProjectMember, (ProjectMember.project_id == Project.id) & (ProjectMember.user_id == user_id)
    ).where(Project.visibility == "public", or_(Project.owner_id == user_id, ProjectMember.user_id == user_id))
      .order_by(Project.updated_at.desc(), Project.id.desc()))).all()
    return [{"id": p.id, "slug": p.slug, "title": p.title, "summary": p.summary,
             "role": "owner" if p.owner_id == user_id else role} for p, role in rows]


async def public_projects_for_users(db, user_ids):
    if not user_ids:
        return {}
    rows = (await db.execute(select(Project, ProjectMember.user_id, ProjectMember.role).outerjoin(
        ProjectMember, (ProjectMember.project_id == Project.id) & (ProjectMember.user_id.in_(user_ids))
    ).where(Project.visibility == "public", or_(Project.owner_id.in_(user_ids), ProjectMember.user_id.in_(user_ids)))
      .order_by(Project.updated_at.desc(), Project.id.desc()))).all()
    result = {user_id: [] for user_id in user_ids}
    for project, member_id, role in rows:
        for user_id, member_role in ((project.owner_id, "owner"), (member_id, role)):
            if user_id in result and not any(item["id"] == project.id for item in result[user_id]):
                result[user_id].append({"id": project.id, "slug": project.slug, "title": project.title,
                                        "summary": project.summary, "role": member_role})
    return result


@router.get("/me/collaboration-profile", response_model=CollaborationProfileResponse)
async def get_profile(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    profile = await db.get(CollaborationProfile, user.id)
    if profile is None:
        return CollaborationProfileResponse(user_id=user.id, updated_at=datetime.now(timezone.utc))
    return profile


@router.put("/me/collaboration-profile", response_model=CollaborationProfileResponse)
async def put_profile(body: CollaborationProfileInput, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    actor = await db.scalar(select(User.id).where(User.id == user.id).with_for_update())
    if actor is None:
        raise HTTPException(401, "Account no longer exists")
    profile = await db.get(CollaborationProfile, user.id, with_for_update=True)
    if profile is None:
        profile = CollaborationProfile(user_id=user.id)
        db.add(profile)
    for key, value in body.model_dump().items():
        setattr(profile, key, value)
    profile.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/people", response_model=Page[PublicPerson])
async def people(params: Annotated[PeopleParams, Query()], db: AsyncSession = Depends(get_db)):
    scope = cursor_scope("people", search=params.search, skill=params.skill, wanted_skill=params.wanted_skill,
                         intent_kind=params.intent_kind, language=params.language)
    cursor = decode_cursor(params.cursor, scope)
    query = select(User, CollaborationProfile).join(CollaborationProfile).where(*discoverable_profile())
    if params.skill:
        query = query.where(CollaborationProfile.skills.contains([params.skill.strip().lower()]))
    if params.wanted_skill:
        query = query.where(CollaborationProfile.wanted_skills.contains([params.wanted_skill.strip().lower()]))
    if params.intent_kind:
        query = query.where(CollaborationProfile.intent_kind == params.intent_kind)
    if params.language:
        query = query.where(CollaborationProfile.languages.contains([params.language.strip().lower()]))
    if params.search and params.search.strip():
        term = params.search.strip().lower()
        pattern = f"%{term}%"
        matches = [User.username.ilike(pattern), User.display_name.ilike(pattern), User.bio.ilike(pattern),
                   CollaborationProfile.intent_text.ilike(pattern),
                   func.array_to_string(CollaborationProfile.skills, " ").ilike(pattern),
                   func.array_to_string(CollaborationProfile.interests, " ").ilike(pattern),
                   func.array_to_string(CollaborationProfile.wanted_skills, " ").ilike(pattern)]
        labels = [term]
        if term in {"game dev", "gamedev", "game development", "game-development"}:
            labels = ["game dev", "gamedev", "game development", "game-development"]
        query = query.where(or_(*matches, CollaborationProfile.skills.overlap(labels),
                                CollaborationProfile.interests.overlap(labels), CollaborationProfile.wanted_skills.overlap(labels)))
    if cursor:
        query = query.where(tuple_(CollaborationProfile.updated_at, User.id) < tuple_(cursor.created_at, cursor.id))
    rows = (await db.execute(query.order_by(CollaborationProfile.updated_at.desc(), User.id.desc()).limit(params.limit + 1))).all()
    records, more = rows[:params.limit], len(rows) > params.limit
    public = await public_projects_for_users(db, [user.id for user, _ in records])
    items = []
    for user, profile in records:
        projects = public.get(user.id, [])
        items.append(person_data(user, profile, [p for p in projects if p["role"] == "owner"],
                                 [p for p in projects if p["role"] != "owner"]))
    return {"items": items, "has_more": more,
            "next_cursor": encode_cursor(records[-1][1].updated_at, records[-1][0].id, scope) if more else None}


@router.get("/people/{user_id}", response_model=PublicPerson)
async def person(user_id: DatabaseId, db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(User, CollaborationProfile).join(CollaborationProfile).where(
        User.id == user_id, *discoverable_profile()))).first()
    if row is None:
        raise HTTPException(404, "Person not found")
    user, profile = row
    projects = await public_projects(db, user.id)
    return person_data(user, profile, [p for p in projects if p["role"] == "owner"],
                       [p for p in projects if p["role"] != "owner"])


@router.get("/people/{user_id}/projects")
async def person_projects(user_id: DatabaseId, db: AsyncSession = Depends(get_db)):
    if await db.get(User, user_id) is None:
        raise HTTPException(404, "Person not found")
    return {"items": await public_projects(db, user_id)}


@router.get("/profile/{username}", response_class=HTMLResponse, include_in_schema=False)
async def profile_share(username: str, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.username == username))
    if user is None:
        raise HTTPException(404, "Profile not found")
    projects = await public_projects(db, user.id)
    cards = "".join(f'<li><a href="/project/{escape(p["slug"], quote=True)}">{escape(p["title"])}</a><p>{escape(p["summary"])}</p></li>' for p in projects)
    name = user.display_name or user.username
    profile = await db.get(CollaborationProfile, user.id)
    fresh = profile is not None and profile.discoverable and profile.status == "active" and profile.intent_kind is not None and profile.updated_at >= datetime.now(timezone.utc) - timedelta(days=30)
    intent = ""
    if fresh:
        links = "".join(f'<li><a href="{escape(url, quote=True)}" rel="noopener noreferrer">{escape(url)}</a></li>' for url in profile.external_links)
        intent = f'<section><h2>{escape(profile.intent_kind.replace("_", " ").title())}</h2><p>{escape(profile.intent_text or "")}</p><p>{escape(", ".join(profile.skills))}</p><p>{escape(", ".join(profile.interests))}</p><ul>{links}</ul></section>'
    body = f'<article><h1>{escape(name)}</h1><p>@{escape(user.username)}</p><p>{escape(user.bio)}</p>{intent}<section><h2>Public projects</h2><ul>{cards}</ul></section><p><a href="/app#profile/{user.id}">Open in Krug</a></p></article>'
    return public_page(name, user.bio, f"/profile/{user.username}", body)


def opening_visible():
    return select(ProjectOpening).join(Project).where(
        ProjectOpening.status == "open", Project.visibility == "public", Project.owner_id.is_not(None),
        Project.status.not_in(["stale", "archived"]))


@router.get("/openings", response_model=Page[OpeningResponse])
async def search_openings(params: Annotated[OpeningSearchParams, Query()], db: AsyncSession = Depends(get_db)):
    scope = cursor_scope("openings", search=params.search, skill=params.skill)
    cursor = decode_cursor(params.cursor, scope)
    query = opening_visible()
    if params.skill:
        query = query.where(ProjectOpening.skills.contains([params.skill.strip().lower()]))
    if params.search and params.search.strip():
        pattern = f"%{params.search.strip()}%"
        query = query.where(or_(ProjectOpening.title.ilike(pattern), ProjectOpening.role.ilike(pattern), ProjectOpening.description.ilike(pattern)))
    query = query.options(selectinload(ProjectOpening.project))
    rows = (await db.scalars(seek_page(query, ProjectOpening, cursor, params.limit))).all()
    return make_page(rows, params.limit, scope)


@router.get("/projects/{slug}/openings", response_model=Page[OpeningResponse])
async def project_openings(slug: str, params: Annotated[PageParams, Query()], db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    project = await get_project(db, slug, user)
    query = select(ProjectOpening).where(ProjectOpening.project_id == project.id)
    if project.owner_id != getattr(user, "id", None):
        query = query.join(Project, Project.id == ProjectOpening.project_id).where(
            ProjectOpening.status == "open", Project.status.not_in(["stale", "archived"]))
    scope = cursor_scope("project_openings", project_id=project.id, owner=project.owner_id if project.owner_id == getattr(user, "id", None) else None)
    query = query.options(selectinload(ProjectOpening.project))
    return make_page((await db.scalars(seek_page(query, ProjectOpening, decode_cursor(params.cursor, scope), params.limit))).all(), params.limit, scope)


@router.post("/projects/{slug}/openings", response_model=OpeningResponse, status_code=201)
async def create_opening(slug: str, body: OpeningInput, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    project = await get_project(db, slug, user, owned=True, lock=True)
    if project.owner_id is None:
        raise HTTPException(403, "An owner is required to open roles")
    if body.status == "open" and (project.visibility != "public" or project.status in {"stale", "archived"}):
        raise HTTPException(422, "Publish an active project before opening a role")
    opening = ProjectOpening(project_id=project.id, **body.model_dump())
    db.add(opening)
    await db.commit()
    await db.refresh(opening)
    opening.project = project
    return opening


@router.patch("/projects/{slug}/openings/{opening_id}", response_model=OpeningResponse)
async def edit_opening(slug: str, opening_id: DatabaseId, body: OpeningPatch, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    project = await get_project(db, slug, user, owned=True, lock=True)
    opening = await db.scalar(select(ProjectOpening).where(ProjectOpening.id == opening_id, ProjectOpening.project_id == project.id).with_for_update())
    if opening is None:
        raise HTTPException(404, "Opening not found")
    values = body.model_dump(exclude_unset=True)
    if values.get("status", opening.status) == "open" and (project.visibility != "public" or project.status in {"stale", "archived"}):
        raise HTTPException(422, "Publish an active project before opening a role")
    for key, value in values.items():
        setattr(opening, key, value)
    await db.commit()
    await db.refresh(opening)
    opening.project = project
    return opening


@router.delete("/projects/{slug}/openings/{opening_id}", status_code=204)
async def delete_opening(slug: str, opening_id: DatabaseId, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    project = await get_project(db, slug, user, owned=True, lock=True)
    opening = await db.scalar(select(ProjectOpening).where(ProjectOpening.id == opening_id, ProjectOpening.project_id == project.id).with_for_update())
    if opening is None:
        raise HTTPException(404, "Opening not found")
    if await db.scalar(select(func.count()).select_from(ProjectApplication).where(ProjectApplication.opening_id == opening.id)):
        raise HTTPException(409, "Close this opening to preserve its applications")
    await db.delete(opening)
    await db.commit()


@router.put("/projects/{slug}/contact-settings", status_code=204)
async def contact_settings(slug: str, body: ContactSettings, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    project = await get_project(db, slug, user, owned=True, lock=True)
    project.owner_contact_url = body.owner_contact_url
    await db.commit()


@router.get("/projects/{slug}/contact-settings", response_model=ContactSettings)
async def read_contact_settings(slug: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    project = await get_project(db, slug, user, owned=True)
    return {"owner_contact_url": project.owner_contact_url}


@router.get("/projects/{slug}/members")
async def project_members(slug: str, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    project = await get_project(db, slug, user)
    rows = (await db.execute(select(ProjectMember, User).join(User).where(
        ProjectMember.project_id == project.id).order_by(ProjectMember.joined_at, ProjectMember.id))).all()
    return {"items": [{"id": member.id, "user_id": person.id, "username": person.username,
                       "display_name": person.display_name, "role": member.role, "joined_at": member.joined_at}
                      for member, person in rows]}


def application_result(application, applicant, project, opening, owner_url=None, applicant_url=None):
    return {"id": application.id, "opening_id": application.opening_id, "applicant_id": applicant.id,
            "applicant_username": applicant.username, "project_slug": project.slug,
            "project_title": project.title, "opening_title": opening.title, "role": opening.role,
            "message": application.message,
            "status": application.status, "created_at": application.created_at,
            "updated_at": application.updated_at, "owner_contact_url": owner_url,
            "applicant_contact_url": applicant_url}


@router.post("/projects/{slug}/openings/{opening_id}/applications", response_model=ProjectApplicationResponse, status_code=201)
async def apply_to_opening(slug: str, opening_id: DatabaseId, body: ApplicationCreate, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "project-application", str(user.id))
    await db.scalar(select(User.id).where(User.id == user.id).with_for_update(read=True, key_share=True))
    project = await get_project(db, slug, lock=True)
    opening = await db.scalar(select(ProjectOpening).where(ProjectOpening.id == opening_id, ProjectOpening.project_id == project.id).with_for_update())
    if (project.owner_id is None or opening is None or opening.status != "open"
            or project.visibility != "public" or project.status in {"stale", "archived"}):
        raise HTTPException(404, "Opening not found")
    if project.owner_id == user.id:
        raise HTTPException(409, "Project owners cannot apply to their own openings")
    app = ProjectApplication(opening_id=opening.id, applicant_id=user.id, **body.model_dump())
    db.add(app)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "You already applied to this opening") from None
    await db.refresh(app)
    return application_result(app, user, project, opening)


async def application_query(db, query):
    rows = (await db.execute(query)).all()
    output = []
    for app, opening, project, applicant in rows:
        accepted = app.status == "accepted"
        output.append(application_result(app, applicant, project, opening,
            project.owner_contact_url if accepted else None,
            app.applicant_contact_url if accepted else None))
    return output


@router.get("/projects/{slug}/applications", response_model=list[ProjectApplicationResponse])
async def owner_applications(slug: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    project = await get_project(db, slug, user, owned=True)
    query = (select(ProjectApplication, ProjectOpening, Project, User).select_from(ProjectApplication)
        .join(ProjectOpening, ProjectOpening.id == ProjectApplication.opening_id)
        .join(Project, Project.id == ProjectOpening.project_id)
        .join(User, User.id == ProjectApplication.applicant_id)
        .where(Project.id == project.id)
        .order_by(ProjectApplication.created_at.desc(), ProjectApplication.id.desc()))
    return await application_query(db, query)


@router.get("/me/applications", response_model=list[ProjectApplicationResponse])
async def my_applications(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    query = (select(ProjectApplication, ProjectOpening, Project, User).select_from(ProjectApplication)
        .join(ProjectOpening, ProjectOpening.id == ProjectApplication.opening_id)
        .join(Project, Project.id == ProjectOpening.project_id)
        .join(User, User.id == ProjectApplication.applicant_id)
        .where(ProjectApplication.applicant_id == user.id)
        .order_by(ProjectApplication.created_at.desc(), ProjectApplication.id.desc()))
    return await application_query(db, query)


@router.patch("/projects/{slug}/applications/{application_id}", response_model=ProjectApplicationResponse)
async def decide_application(slug: str, application_id: DatabaseId, body: ApplicationStatus, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await db.scalar(select(User.id).where(User.id == user.id).with_for_update(read=True, key_share=True))
    brief = (await db.execute(select(ProjectApplication.applicant_id, ProjectOpening.project_id, ProjectOpening.role)
        .join(ProjectOpening).join(Project).where(Project.slug == slug, Project.owner_id == user.id,
            ProjectApplication.id == application_id))).first()
    if brief is None:
        raise HTTPException(404, "Application not found")
    if body.status == "accepted":
        await db.scalar(select(User.id).where(User.id == brief.applicant_id).with_for_update(read=True, key_share=True))
    project = await db.scalar(select(Project).where(Project.slug == slug, Project.owner_id == user.id)
                               .execution_options(populate_existing=True).with_for_update())
    row = (await db.execute(select(ProjectApplication, ProjectOpening).join(ProjectOpening).where(
        ProjectApplication.id == application_id, ProjectOpening.project_id == project.id
    ).with_for_update(of=ProjectApplication, nowait=False))).first()
    if row is None:
        raise HTTPException(404, "Application not found")
    application, opening = row
    if application.status != "pending":
        if application.status == body.status:
            pass
        else:
            raise HTTPException(409, "Application has already been decided")
    else:
        application.status = body.status
        application.updated_at = datetime.now(timezone.utc)
    if body.status == "accepted":
        await db.execute(insert(ProjectMember).values(project_id=project.id, user_id=application.applicant_id, role=opening.role)
                         .on_conflict_do_nothing(constraint="uq_project_member"))
    if application.status == body.status:
        await db.commit()
    await db.refresh(application)
    applicant = await db.get(User, application.applicant_id)
    return application_result(application, applicant, project, opening,
        project.owner_contact_url if application.status == "accepted" else None,
        application.applicant_contact_url if application.status == "accepted" else None)


@router.post("/me/applications/{application_id}/withdraw", response_model=ProjectApplicationResponse)
async def withdraw_application(application_id: DatabaseId, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await db.scalar(select(User.id).where(User.id == user.id).with_for_update(read=True, key_share=True))
    app = await db.scalar(select(ProjectApplication).where(ProjectApplication.id == application_id, ProjectApplication.applicant_id == user.id))
    if app is None:
        raise HTTPException(404, "Application not found")
    opening = await db.get(ProjectOpening, app.opening_id)
    project = await db.scalar(select(Project).where(Project.id == opening.project_id)
                              .execution_options(populate_existing=True).with_for_update())
    app = await db.scalar(select(ProjectApplication).where(ProjectApplication.id == application_id)
                          .execution_options(populate_existing=True).with_for_update())
    if app.status == "pending":
        app.status = "withdrawn"
        app.updated_at = datetime.now(timezone.utc)
        await db.commit()
    elif app.status not in {"withdrawn"}:
        raise HTTPException(409, "Only pending applications can be withdrawn")
    return application_result(app, user, project, opening,
        project.owner_contact_url if app.status == "accepted" else None,
        app.applicant_contact_url if app.status == "accepted" else None)


@router.post("/external-submissions", status_code=201)
async def submit_external_project(body: ExternalSubmissionInput, request: Request,
                                  db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "external-submission", str(user.id))
    submission = ExternalSubmission(submitted_by=user.id, **body.model_dump())
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return {"id": submission.id, "status": submission.status, "created_at": submission.created_at}


@router.get("/admin/external-submissions")
async def pending_external_submissions(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    rows = (await db.scalars(select(ExternalSubmission).where(ExternalSubmission.status == "pending")
                             .order_by(ExternalSubmission.created_at, ExternalSubmission.id))).all()
    return {"items": [{"id": x.id, "title": x.title, "summary": x.summary, "description": x.description,
                       "tags": x.tags, "skills": x.skills, "source_url": x.source_url,
                       "submitted_by": x.submitted_by, "created_at": x.created_at} for x in rows]}


@router.patch("/admin/external-submissions/{submission_id}")
async def review_external_submission(submission_id: DatabaseId, body: ReviewDecision,
                                     db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    submission = await db.scalar(select(ExternalSubmission).where(ExternalSubmission.id == submission_id).with_for_update())
    if submission is None:
        raise HTTPException(404, "Submission not found")
    if submission.status != "pending":
        raise HTTPException(409, "Submission has already been reviewed")
    project_id = None
    if body.status == "approved":
        project = Project(slug=f"manual-project-{submission.id}", title=submission.title,
            summary=submission.summary, description=submission.description, origin="external",
            status="active", stage="unknown", visibility="public", owner_id=None,
            submitted_by=submission.submitted_by, tags=submission.tags, skills=submission.skills,
            recruitment_status="unknown", source_name="manual", source_url=submission.source_url,
            canonical_url=canonical_project_url(submission.source_url), last_activity_at=None)
        db.add(project)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(409, "A project with this source URL already exists") from None
        project_id = project.id
    submission.status = body.status
    submission.project_id = project_id
    submission.reviewed_by = admin.id
    submission.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": submission.id, "status": submission.status, "project_id": project_id}


@router.post("/projects/{slug}/claims", status_code=201)
async def submit_project_claim(slug: str, body: ClaimInput, request: Request,
                               db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "project-claim", str(user.id))
    project = await get_project(db, slug, user, lock=True)
    if project.origin != "external" or project.owner_id is not None:
        raise HTTPException(409, "This project cannot be claimed")
    if await db.scalar(select(ProjectClaim.id).where(ProjectClaim.project_id == project.id,
            ProjectClaim.requester_id == user.id, ProjectClaim.status == "pending")):
        raise HTTPException(409, "You already have a pending claim")
    claim = ProjectClaim(project_id=project.id, requester_id=user.id, **body.model_dump())
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return {"id": claim.id, "project_id": project.id, "status": claim.status, "created_at": claim.created_at}


@router.get("/admin/project-claims")
async def pending_project_claims(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    rows = (await db.execute(select(ProjectClaim, Project).join(Project).where(ProjectClaim.status == "pending")
        .order_by(ProjectClaim.created_at, ProjectClaim.id))).all()
    return {"items": [{"id": claim.id, "project_id": project.id, "project_slug": project.slug,
        "project_title": project.title, "requester_id": claim.requester_id,
        "evidence_url": claim.evidence_url, "evidence_text": claim.evidence_text,
        "created_at": claim.created_at} for claim, project in rows]}


@router.patch("/admin/project-claims/{claim_id}")
async def review_project_claim(claim_id: DatabaseId, body: ReviewDecision,
                               db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    claim = await db.scalar(select(ProjectClaim).where(ProjectClaim.id == claim_id))
    if claim is None:
        raise HTTPException(404, "Claim not found")
    requester_exists = await db.scalar(select(User.id).where(User.id == claim.requester_id)
                                       .with_for_update(read=True, key_share=True))
    if requester_exists is None:
        raise HTTPException(404, "Claim not found")
    project = await db.scalar(select(Project).where(Project.id == claim.project_id).with_for_update())
    claim = await db.scalar(select(ProjectClaim).where(ProjectClaim.id == claim_id)
                            .execution_options(populate_existing=True).with_for_update())
    if claim is None:
        raise HTTPException(404, "Claim not found")
    if claim.status != "pending":
        raise HTTPException(409, "Claim has already been reviewed")
    if body.status == "approved":
        if project.origin != "external" or project.owner_id is not None:
            raise HTTPException(409, "Project is already claimed")
        project.owner_id = claim.requester_id
        project.claimed_at = datetime.now(timezone.utc)
        await db.execute(insert(ProjectMember).values(project_id=project.id, user_id=claim.requester_id, role="Owner")
                         .on_conflict_do_nothing(constraint="uq_project_member"))
    claim.status = body.status
    claim.reviewed_by = admin.id
    claim.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": claim.id, "status": claim.status, "project_id": project.id}
