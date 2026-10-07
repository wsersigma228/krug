from datetime import datetime, timezone
from html import escape
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import Float, case, cast, func, select, tuple_, update, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import PUBLIC_APP_URL
from backend.database import get_db
from backend.models import EmailDelivery, Post, Project, ProjectEngagement, ProjectMember, ProjectOpening, User
from backend.pagination import cursor_scope, decode_cursor, encode_cursor, make_page, seek_page
from backend.project_schemas import (DiscoveryParams, EngagementPatch, EngagementResponse,
    DiscoveryProjectResponse, InterestedUser, ProjectCreate, ProjectPatch, ProjectResponse)
from backend.schemas import Page, PageParams, PostResponse
from backend.security import get_current_user, get_optional_user
from backend.project_access import canonical_project_url
from backend.rate_limit import check_rate_limit

router = APIRouter()


async def with_project_counts(db, projects):
    projects = list(projects)
    if not projects:
        return []
    ids = [project.id for project in projects]
    queries = (
        select(ProjectEngagement.project_id, func.count()).where(
            ProjectEngagement.project_id.in_(ids), ProjectEngagement.interested.is_(True),
            ProjectEngagement.interested_visible.is_(True)).group_by(ProjectEngagement.project_id),
        select(ProjectMember.project_id, func.count()).where(ProjectMember.project_id.in_(ids)).group_by(ProjectMember.project_id),
        select(ProjectOpening.project_id, func.count()).join(Project).where(
            ProjectOpening.project_id.in_(ids), ProjectOpening.status == "open",
            Project.status.not_in(["stale", "archived"])).group_by(ProjectOpening.project_id),
        select(Post.project_id, func.count()).where(Post.project_id.in_(ids), Post.is_published.is_(True)).group_by(Post.project_id),
    )
    grouped = []
    for query in queries:
        grouped.append({project_id: count for project_id, count in (await db.execute(query)).all()})
    return [DiscoveryProjectResponse.model_validate(project).model_copy(update={
        "interested_count": grouped[0].get(project.id, 0), "member_count": grouped[1].get(project.id, 0),
        "open_roles_count": grouped[2].get(project.id, 0), "published_updates_count": grouped[3].get(project.id, 0),
    }) for project in projects]


async def get_project(db, slug, user=None, *, owned=False, lock=False):
    query = select(Project).where(Project.slug == slug)
    if lock:
        query = query.execution_options(populate_existing=True).with_for_update()
    project = await db.scalar(query)
    if project is None or (owned or project.visibility != "public") and (
        user is None or project.owner_id != user.id
    ):
        raise HTTPException(404, "Project not found")
    return project


@router.get("/discovery", response_model=Page[DiscoveryProjectResponse])
async def discovery(params: Annotated[DiscoveryParams, Query()], db: AsyncSession = Depends(get_db)):
    filters = params.model_dump(exclude={"cursor", "limit"})
    search = (params.search or "").strip()
    scope = cursor_scope("discovery", **filters)
    cursor = decode_cursor(params.cursor, scope, ranked=bool(search))
    query = select(Project).where(Project.visibility == "public")
    if params.tag:
        query = query.where(Project.tags.contains([params.tag.strip().lower()]))
    if params.skill:
        query = query.where(Project.skills.contains([params.skill.strip().lower()]))
    if params.source:
        if params.source in {"native", "external"}:
            query = query.where(Project.origin == params.source)
        else:
            query = query.where(Project.source_name == params.source)
    if params.status:
        query = query.where(Project.status == params.status)
    elif params.active is None:
        query = query.where(Project.status.not_in(["stale", "archived"]))
    if params.recruitment_status:
        query = query.where(Project.recruitment_status == params.recruitment_status)
    if params.active is not None:
        query = query.where(Project.status == "active" if params.active else Project.status != "active")
    if not search:
        activity = func.coalesce(Project.last_activity_at, Project.created_at)
        if cursor:
            query = query.where(tuple_(activity, Project.id) < tuple_(cursor.created_at, cursor.id))
        rows = (await db.scalars(query.order_by(activity.desc(), Project.id.desc()).limit(params.limit + 1))).all()
        selected, more = rows[:params.limit], len(rows) > params.limit
        page = {"items": selected, "has_more": more,
                "next_cursor": encode_cursor(selected[-1].last_activity_at or selected[-1].created_at, selected[-1].id, scope) if more else None}
        page["items"] = await with_project_counts(db, page["items"])
        return page
    terms = func.websearch_to_tsquery("pg_catalog.simple", search)
    labels = [search.lower()]
    if search.lower() in {"game dev", "gamedev", "game development", "game-development"}:
        labels = ["game dev", "gamedev", "game development", "game-development"]
    pattern = f"%{search}%"
    role_match = select(ProjectOpening.id).where(ProjectOpening.project_id == Project.id,
        ProjectOpening.status == "open", or_(ProjectOpening.title.ilike(pattern), ProjectOpening.role.ilike(pattern),
            ProjectOpening.description.ilike(pattern), ProjectOpening.skills.overlap(labels))).exists()
    rank = cast(func.ts_rank(Project.search_vector, terms) + case((role_match, 0.25), else_=0), Float(53))
    query = query.add_columns(rank.label("rank")).where(or_(
        Project.search_vector.bool_op("@@")(terms), Project.tags.overlap(labels),
        Project.skills.overlap(labels), role_match,
    ))
    activity = func.coalesce(Project.last_activity_at, Project.created_at)
    if cursor:
        query = query.where(tuple_(rank, activity, Project.id) < tuple_(cursor.rank, cursor.created_at, cursor.id))
    rows = (await db.execute(query.order_by(rank.desc(), activity.desc(), Project.id.desc()).limit(params.limit + 1))).all()
    items, more = rows[:params.limit], len(rows) > params.limit
    projects = await with_project_counts(db, [project for project, _ in items])
    return {"items": projects, "has_more": more,
            "next_cursor": encode_cursor(items[-1][0].last_activity_at or items[-1][0].created_at, items[-1][0].id, scope, rank=items[-1][1]) if more else None}


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(body: ProjectCreate, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "project-create", str(user.id))
    # Serialize owner deletion with creating the FK reference.
    actor = await db.scalar(select(User.id).where(User.id == user.id).with_for_update(read=True, key_share=True))
    if actor is None:
        raise HTTPException(401, "Account no longer exists")
    project = Project(**body.model_dump(), owner_id=user.id, origin="native", canonical_url=None if body.derived_from_project_id else canonical_project_url(body.source_url),
                      last_activity_at=datetime.now(timezone.utc) if body.visibility == "public" else None)
    db.add(project)
    try:
        if body.derived_from_project_id is not None:
            source = await db.scalar(select(Project).where(Project.id == body.derived_from_project_id,
                Project.origin == "external", Project.visibility == "public").with_for_update(read=True))
            if source is None:
                raise HTTPException(404, "Source project not found")
        await db.flush()
        db.add(ProjectMember(project_id=project.id, user_id=user.id, role="Owner"))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Project slug or source URL already exists") from None
    await db.refresh(project)
    return project


@router.get("/me/projects", response_model=Page[ProjectResponse])
async def my_projects(params: Annotated[PageParams, Query()], db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    scope = cursor_scope("my_projects", user_id=user.id)
    rows = (await db.scalars(seek_page(select(Project).where(Project.owner_id == user.id), Project,
                                     decode_cursor(params.cursor, scope), params.limit))).all()
    return make_page(rows, params.limit, scope)


@router.get("/me/saved-projects", response_model=Page[ProjectResponse])
async def saved_projects(params: Annotated[PageParams, Query()], db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    scope = cursor_scope("saved_projects", user_id=user.id)
    query = select(Project).join(ProjectEngagement, ProjectEngagement.project_id == Project.id).where(
        ProjectEngagement.user_id == user.id, ProjectEngagement.saved.is_(True), Project.visibility == "public")
    rows = (await db.scalars(seek_page(query, Project, decode_cursor(params.cursor, scope), params.limit))).all()
    return make_page(rows, params.limit, scope)


@router.get("/me/followed-projects", response_model=Page[ProjectResponse])
async def followed_projects(params: Annotated[PageParams, Query()], db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    scope = cursor_scope("followed_projects", user_id=user.id)
    query = select(Project).join(ProjectEngagement, ProjectEngagement.project_id == Project.id).where(
        ProjectEngagement.user_id == user.id, ProjectEngagement.following.is_(True), Project.visibility == "public")
    rows = (await db.scalars(seek_page(query, Project, decode_cursor(params.cursor, scope), params.limit))).all()
    return make_page(rows, params.limit, scope)


@router.get("/projects/{slug}", response_model=DiscoveryProjectResponse)
async def project_detail(slug: str, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    project = await get_project(db, slug, user)
    return (await with_project_counts(db, [project]))[0]


@router.patch("/projects/{slug}", response_model=ProjectResponse)
async def edit_project(slug: str, body: ProjectPatch, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    project = await get_project(db, slug, user, owned=True, lock=True)
    changes = body.model_dump(exclude_unset=True)
    if project.origin == "external" and "source_url" in changes:
        raise HTTPException(422, "External source identity is preserved")
    for key, value in changes.items():
        setattr(project, key, value)
    if "source_url" in body.model_fields_set:
        project.canonical_url = canonical_project_url(body.source_url)
    if project.visibility != "public":
        await db.execute(update(EmailDelivery).where(EmailDelivery.post_id.in_(
            select(Post.id).where(Post.project_id == project.id)), EmailDelivery.status == "pending").values(status="cancelled"))
    if project.visibility == "public":
        project.last_activity_at = datetime.now(timezone.utc)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Source URL already belongs to a project") from None
    await db.refresh(project)
    return project


@router.get("/projects/{slug}/updates", response_model=Page[PostResponse])
async def project_updates(slug: str, params: Annotated[PageParams, Query()], db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    project = await get_project(db, slug, user)
    query = select(Post).where(Post.project_id == project.id)
    viewer_scope = None
    if user is None:
        query = query.where(Post.is_published.is_(True))
    else:
        is_member = project.owner_id == user.id or await db.scalar(select(ProjectMember.id).where(
            ProjectMember.project_id == project.id, ProjectMember.user_id == user.id)) is not None
        if is_member:
            query = query.where(or_(Post.is_published.is_(True), Post.author_id == user.id))
            viewer_scope = user.id
        else:
            query = query.where(Post.is_published.is_(True))
    scope_values = {"project_id": project.id,
                    "owner": user.id if user and user.id == project.owner_id else None}
    if viewer_scope is not None and user.id != project.owner_id:
        scope_values["viewer"] = viewer_scope
    scope = cursor_scope("project_updates", **scope_values)
    rows = (await db.scalars(seek_page(query, Post, decode_cursor(params.cursor, scope), params.limit))).all()
    return make_page(rows, params.limit, scope)


@router.get("/projects/{slug}/engagement", response_model=EngagementResponse)
async def engagement(slug: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    project = await get_project(db, slug, user)
    return await db.scalar(select(ProjectEngagement).where(ProjectEngagement.project_id == project.id,
                                                         ProjectEngagement.user_id == user.id)) or EngagementResponse()


@router.patch("/projects/{slug}/engagement", response_model=EngagementResponse)
async def change_engagement(slug: str, body: EngagementPatch, request: Request, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "project-engagement", str(user.id))
    actor = await db.scalar(select(User.id).where(User.id == user.id).with_for_update(read=True, key_share=True))
    if actor is None:
        raise HTTPException(401, "Account no longer exists")
    project = await get_project(db, slug, user)
    await db.execute(insert(ProjectEngagement).values(project_id=project.id, user_id=user.id)
                     .on_conflict_do_nothing(constraint="uq_project_engagement_user"))
    state = await db.scalar(select(ProjectEngagement).where(ProjectEngagement.project_id == project.id,
                           ProjectEngagement.user_id == user.id).execution_options(populate_existing=True).with_for_update())
    values = body.model_dump(exclude_unset=True)
    interested = values.get("interested", state.interested)
    if not interested and values.get("interested_visible"):
        raise HTTPException(422, "Public interest requires interested=true")
    if not interested:
        values["interested_visible"] = False
    for key, value in values.items():
        setattr(state, key, value)
    await db.commit()
    return state


@router.get("/projects/{slug}/interested", response_model=Page[InterestedUser])
async def interested_users(slug: str, params: Annotated[PageParams, Query()], db: AsyncSession = Depends(get_db)):
    project = await get_project(db, slug)
    scope = cursor_scope("project_interested", project_id=project.id)
    query = select(ProjectEngagement.id, ProjectEngagement.created_at, User.id.label("user_id"),
                   User.username, User.display_name, User.bio).join(User, User.id == ProjectEngagement.user_id).where(
        ProjectEngagement.project_id == project.id, ProjectEngagement.interested.is_(True), ProjectEngagement.interested_visible.is_(True))
    rows = (await db.execute(seek_page(query, ProjectEngagement, decode_cursor(params.cursor, scope), params.limit))).all()
    page = make_page(rows, params.limit, scope)
    page["items"] = [{"id": row.user_id, "username": row.username, "display_name": row.display_name, "bio": row.bio} for row in page["items"]]
    return page


def public_page(title, summary, path, body, image=None):
    url = PUBLIC_APP_URL + path
    image_url = escape(PUBLIC_APP_URL + (image or "/assets/og-default.png"), quote=True)
    image_meta = f'<meta property="og:image" content="{image_url}"><meta name="twitter:image" content="{image_url}">'
    return HTMLResponse(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · Krug</title><link rel="icon" href="/assets/favicon.svg"><meta name="description" content="{escape(summary, quote=True)}">
<link rel="canonical" href="{escape(url, quote=True)}"><meta property="og:type" content="article"><meta property="og:title" content="{escape(title, quote=True)}">
<meta property="og:description" content="{escape(summary, quote=True)}"><meta property="og:url" content="{escape(url, quote=True)}">{image_meta}
<meta property="og:site_name" content="Krug"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{escape(title, quote=True)}"><meta name="twitter:description" content="{escape(summary, quote=True)}"><link rel="stylesheet" href="/assets/share.css"></head><body>
<header class="share-header"><a class="share-brand" href="/app">Krug</a><a class="share-app" href="/app">Discover projects</a></header><main class="share-main">{body}</main></body></html>''', headers={
        "Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
        "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    })


@router.get("/project/{slug}", response_class=HTMLResponse, include_in_schema=False)
async def project_page(slug: str, db: AsyncSession = Depends(get_db)):
    project = await get_project(db, slug)
    owner = await db.get(User, project.owner_id) if project.owner_id is not None else None
    byline = f'<p class="share-byline">By {escape(owner.display_name or owner.username)}</p>' if owner else ""
    counts = (await with_project_counts(db, [project]))[0]
    updates = (await db.scalars(select(Post).where(Post.project_id == project.id, Post.is_published.is_(True))
                               .order_by(Post.created_at.desc(), Post.id.desc()).limit(20))).all()
    links = "".join(f'<li><a href="/project/{escape(slug)}/updates/{post.id}">{escape(post.title or post.content[:80])}</a><time datetime="{post.created_at.isoformat()}">{post.created_at.date()}</time></li>' for post in updates)
    source_label = "GitHub" if project.source_name == "github" else project.source_name or "external source"
    source = f'<a class="share-secondary" href="{escape(project.source_url, quote=True)}" rel="noopener noreferrer">View on {escape(source_label)}</a>' if project.source_url else ""
    eyebrow = f'Imported from {escape(source_label)}' if project.origin == "external" else ""
    provenance = f'<p class="share-byline">{eyebrow}</p>' if eyebrow else ""
    tags = "".join(f'<span class="share-tag">{escape(tag)}</span>' for tag in project.tags)
    facts = ""
    if project.last_verified_at:
        facts += f'<div><dt>Source verified</dt><dd>{project.last_verified_at.date()}</dd></div>'
    if project.last_activity_at:
        facts += f'<div><dt>Last activity</dt><dd>{project.last_activity_at.date()}</dd></div>'
    if project.recruitment_status != "unknown":
        facts += f'<div><dt>Recruitment</dt><dd>{escape(project.recruitment_status.capitalize())}</dd></div>'
    if project.commitment:
        facts += f'<div><dt>Commitment</dt><dd>{escape(project.commitment)}</dd></div>'
    if project.experience_level:
        facts += f'<div><dt>Experience</dt><dd>{escape(project.experience_level)}</dd></div>'
    fact_list = f'<dl class="share-facts">{facts}</dl>' if facts else ""
    updates_content = f'<ul class="share-update-list">{links}</ul>' if updates else '<p class="share-empty">No updates published in Krug yet.</p>'
    stats = (f'<dl class="share-facts"><div><dt>Interested people</dt><dd>{counts.interested_count}</dd></div>'
             f'<div><dt>Members</dt><dd>{counts.member_count}</dd></div>'
             f'<div><dt>Open roles</dt><dd>{counts.open_roles_count}</dd></div>'
             f'<div><dt>Published updates</dt><dd>{counts.published_updates_count}</dd></div></dl>')
    roles = []
    if project.status not in {"stale", "archived"}:
        openings = (await db.scalars(select(ProjectOpening).where(
            ProjectOpening.project_id == project.id, ProjectOpening.status == "open")
            .order_by(ProjectOpening.created_at, ProjectOpening.id))).all()
        roles = [f'<li><strong>{escape(opening.title)}</strong><p>{escape(opening.role)}</p>'
                 f'<div class="share-tags">{"".join(f"<span class=\"share-tag\">{escape(skill)}</span>" for skill in opening.skills)}</div>'
                 f'<a href="/app#project/{escape(slug, quote=True)}">View role and apply</a></li>' for opening in openings]
    roles_content = f'<ul class="share-update-list">{"".join(roles)}</ul>' if roles else '<p class="share-empty">No open roles right now.</p>'
    member_rows = (await db.execute(select(ProjectMember, User).join(User).where(
        ProjectMember.project_id == project.id).order_by(ProjectMember.joined_at, ProjectMember.id))).all()
    member_links = "".join(f'<li><a href="/app#profile/{person.id}">{escape(person.display_name or person.username)}</a>'
                            f'<span class="share-byline">{escape(member.role)}</span></li>'
                            for member, person in member_rows)
    members_content = f'<ul class="share-update-list">{member_links}</ul>' if member_links else '<p class="share-empty">No members listed yet.</p>'
    body = f'<article class="share-project"><h1 class="share-title">{escape(project.title)}</h1>{byline}{provenance}<p class="share-summary">{escape(project.summary)}</p><div class="share-meta"><span>{escape(project.status.capitalize())}</span><span>{escape(project.stage.capitalize())}</span></div><div class="share-tags">{tags}</div><div class="prose">{escape(project.description)}</div>{fact_list}{stats}<div class="share-actions"><a class="share-primary" href="/app#project/{escape(slug, quote=True)}">Open project in Krug</a><a class="share-secondary" href="/app#project-interested/{escape(slug, quote=True)}">Interested people</a><a class="share-secondary" href="/app#explore?kind=people">Find people</a><a class="share-secondary" href="/app#explore?kind=openings">Browse roles</a>{source}</div></article><section class="share-updates"><h2>Open roles</h2>{roles_content}</section><section class="share-updates"><h2>Project members</h2>{members_content}</section><section class="share-updates"><h2>Project updates</h2>{updates_content}</section>'
    return public_page(project.title, project.summary, f"/project/{slug}", body)


@router.get("/project/{slug}/updates/{post_id}", response_class=HTMLResponse, include_in_schema=False)
async def update_page(slug: str, post_id: int, db: AsyncSession = Depends(get_db)):
    project = await get_project(db, slug)
    post = await db.scalar(select(Post).where(Post.id == post_id, Post.project_id == project.id, Post.is_published.is_(True)))
    if post is None:
        raise HTTPException(404, "Update not found")
    image = f'<img src="{escape(post.image_url, quote=True)}" alt="Project update image">' if post.image_url else ""
    author = await db.get(User, post.author_id)
    byline = escape(author.display_name or author.username) if author else ""
    body = f'<article class="share-update"><p class="share-backlink"><a href="/project/{slug}">{escape(project.title)}</a></p><h1 class="share-title">{escape(post.title or project.title + " update")}</h1><p class="share-byline">{byline} · <time datetime="{post.created_at.isoformat()}">{post.created_at.date()}</time></p><div class="prose">{escape(post.content)}</div>{image}<div class="share-actions"><a class="share-primary" href="/app#project/{slug}">Explore this project in Krug</a><a class="share-secondary" href="/project/{slug}">View project</a></div></article>'
    return public_page(post.title or project.title + " update", " ".join(post.content.split())[:250], f"/project/{slug}/updates/{post_id}", body, post.image_url)
