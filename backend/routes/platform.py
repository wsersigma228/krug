from datetime import datetime, timezone
from html import escape
from typing import Annotated
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import ValidationError
from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import PUBLIC_APP_URL
from backend.database import get_db
from backend.models import (
    Community, CommunityEngagement, CommunityMember, Comment, Event, EventEngagement,
    Post, Project, ProjectMember, Team, TeamApplication,
    TeamEngagement, TeamMember, TeamOpening, User,
)
from backend.pagination import cursor_scope, decode_cursor, encode_cursor, make_page, seek_page
from backend.platform_schemas import (
    ApplicationInput, ApplicationResponse, ApplicationStatus, CommunityInput, CommunityPatch,
    CommunityParams, CommunityResponse, EngagementPatch, EventInput, EventParams, EventPatch,
    EventResponse, MemberResponse, OpeningInput, OpeningPatch, OpeningResponse, SavePatch,
    TeamInput, TeamParams, TeamPatch, TeamResponse,
)
from backend.project_access import canonical_project_url, public_post
from backend.project_schemas import InterestedUser, ProjectCreate, ProjectResponse
from backend.rate_limit import check_rate_limit
from backend.schemas import Page, PageParams, PostResponse
from backend.security import get_current_user, get_optional_user

router = APIRouter()


def _search_labels(search: str) -> list[str]:
    value = search.strip().lower()
    if value in {"game dev", "gamedev", "game development", "game-development"}:
        return ["game dev", "gamedev", "game development", "game-development"]
    return [value]
DatabaseId = Annotated[int, Path(gt=0, le=2_147_483_647)]


async def lock_actor(db, user_id):
    actor = await db.scalar(select(User.id).where(User.id == user_id)
                            .with_for_update(read=True, key_share=True))
    if actor is None:
        raise HTTPException(401, "Account no longer exists")


async def owned(db, model, slug, user_id, *, lock=False):
    query = select(model).where(model.slug == slug)
    if lock:
        query = query.execution_options(populate_existing=True).with_for_update()
    entity = await db.scalar(query)
    if entity is None or entity.owner_id != user_id:
        raise HTTPException(404, "Not found")
    return entity


async def visible(db, model, slug, user=None, *, lock=False):
    query = select(model).where(model.slug == slug)
    if lock:
        query = query.execution_options(populate_existing=True).with_for_update()
    entity = await db.scalar(query)
    if entity is None or (entity.visibility != "public" and (user is None or entity.owner_id != user.id)):
        raise HTTPException(404, "Not found")
    return entity


def page_response(items, more, last, scope):
    return {"items": items, "has_more": more,
            "next_cursor": encode_cursor(last.created_at, last.id, scope) if more else None}


def canonical_event_url(url):
    if url is None:
        return None
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, ""))


def joined_page(rows, limit, scope):
    items = rows[:limit]
    more = len(rows) > limit
    last = items[-1][0] if more else None
    return {"items": items, "has_more": more,
            "next_cursor": encode_cursor(last.created_at, last.id, scope) if more else None}


async def team_responses(db, rows, user_id=None):
    rows = list(rows)
    if not rows:
        return []
    ids = [row.id for row in rows]
    members_counts = dict((await db.execute(
        select(TeamMember.team_id, func.count()).where(TeamMember.team_id.in_(ids))
        .group_by(TeamMember.team_id))).all())
    openings_counts = dict((await db.execute(
        select(TeamOpening.team_id, func.count()).where(TeamOpening.team_id.in_(ids),
            TeamOpening.status == "open").group_by(TeamOpening.team_id))).all())
    interested_counts = dict((await db.execute(
        select(TeamEngagement.team_id, func.count()).where(TeamEngagement.team_id.in_(ids),
            TeamEngagement.interested.is_(True), TeamEngagement.interested_visible.is_(True))
            .group_by(TeamEngagement.team_id))).all())
    members = {}
    engagement = {}
    if user_id is not None:
        members = dict((await db.execute(select(TeamMember.team_id, func.count()).where(
            TeamMember.team_id.in_(ids), TeamMember.user_id == user_id).group_by(TeamMember.team_id))).all())
        engagement = {key: {"saved": saved, "interested": interested, "interested_visible": visible}
                      for key, saved, interested, visible in (await db.execute(
            select(TeamEngagement.team_id, TeamEngagement.saved, TeamEngagement.interested,
                   TeamEngagement.interested_visible).where(TeamEngagement.user_id == user_id,
                                                              TeamEngagement.team_id.in_(ids)))).all()}
    return [TeamResponse.model_validate(row).model_copy(update={
        "member_count": members_counts.get(row.id, 0), "openings_count": openings_counts.get(row.id, 0),
        "interested_count": interested_counts.get(row.id, 0),
        "saved": engagement.get(row.id, {}).get("saved", False),
        "interested": engagement.get(row.id, {}).get("interested", False),
        "interested_visible": engagement.get(row.id, {}).get("interested_visible", False),
        "is_member": bool(members.get(row.id, 0)),
    }) for row in rows]


async def community_responses(db, rows, user_id=None):
    rows = list(rows)
    if not rows:
        return []
    ids = [row.id for row in rows]
    members_counts = dict((await db.execute(
        select(CommunityMember.community_id, func.count()).where(CommunityMember.community_id.in_(ids))
        .group_by(CommunityMember.community_id))).all())
    published_posts_counts = dict((await db.execute(
        select(Post.community_id, func.count()).where(Post.community_id.in_(ids), public_post())
        .group_by(Post.community_id))).all())
    saved = {}
    member = {}
    if user_id is not None:
        saved = dict((await db.execute(select(CommunityEngagement.community_id, CommunityEngagement.saved).where(
            CommunityEngagement.user_id == user_id, CommunityEngagement.community_id.in_(ids)))).all())
        member = dict((await db.execute(select(CommunityMember.community_id, func.count()).where(
            CommunityMember.community_id.in_(ids), CommunityMember.user_id == user_id)
            .group_by(CommunityMember.community_id))).all())
    return [CommunityResponse.model_validate(row).model_copy(update={
        "member_count": members_counts.get(row.id, 0),
        "published_posts_count": published_posts_counts.get(row.id, 0),
        "saved": saved.get(row.id, False),
        "is_member": bool(member.get(row.id, 0)),
    }) for row in rows]


async def event_responses(db, rows, user_id=None):
    rows = list(rows)
    if not rows:
        return []
    ids = [row.id for row in rows]
    interested = dict((await db.execute(select(EventEngagement.event_id, func.count()).where(
        EventEngagement.event_id.in_(ids), EventEngagement.interested.is_(True),
        EventEngagement.interested_visible.is_(True)).group_by(EventEngagement.event_id))).all())
    state = {}
    if user_id is not None:
        state = {key: {"saved": saved, "interested": is_interested, "interested_visible": visible}
                 for key, saved, is_interested, visible in (await db.execute(
            select(EventEngagement.event_id, EventEngagement.saved, EventEngagement.interested,
                   EventEngagement.interested_visible).where(EventEngagement.user_id == user_id,
                                                              EventEngagement.event_id.in_(ids)))).all()}
    return [EventResponse.model_validate(row).model_copy(update={
        "interested_count": interested.get(row.id, 0),
        "saved": state.get(row.id, {}).get("saved", False),
        "interested": state.get(row.id, {}).get("interested", False),
        "interested_visible": state.get(row.id, {}).get("interested_visible", False),
    }) for row in rows]


@router.get("/communities", response_model=Page[CommunityResponse])
async def list_communities(params: Annotated[CommunityParams, Query()],
                           db: AsyncSession = Depends(get_db),
                           user: User | None = Depends(get_optional_user)):
    values = params.model_dump(exclude={"cursor", "limit"})
    if params.saved is not None and user is None:
        raise HTTPException(401, "Sign in to filter saved communities")
    scope = cursor_scope("communities", user_id=user.id if user else None, **values)
    cursor = decode_cursor(params.cursor, scope)
    query = select(Community).where(or_(Community.visibility == "public",
        Community.owner_id == (user.id if user else -1)))
    if params.saved is not None:
        query = query.outerjoin(CommunityEngagement, (CommunityEngagement.community_id == Community.id)
            & (CommunityEngagement.user_id == user.id)).where(
                func.coalesce(CommunityEngagement.saved, False).is_(params.saved))
    if params.search:
        terms = func.websearch_to_tsquery("pg_catalog.simple", params.search.strip())
        labels = _search_labels(params.search)
        query = query.where(or_(Community.search_vector.bool_op("@@")(terms),
                                Community.skills.overlap(labels), Community.topics.overlap(labels)))
    if params.skill:
        query = query.where(Community.skills.contains([params.skill.strip().lower()]))
    if params.topic:
        query = query.where(Community.topics.contains([params.topic.strip().lower()]))
    if params.language:
        query = query.where(Community.languages.contains([params.language.strip().lower()]))
    if params.format:
        query = query.where(Community.format == params.format)
    rows = (await db.scalars(seek_page(query, Community, cursor, params.limit))).all()
    selected = rows[:params.limit]
    return page_response(await community_responses(db, selected, user.id if user else None),
                         len(rows) > params.limit, selected[-1] if selected else None, scope)


@router.post("/communities", response_model=CommunityResponse, status_code=201)
async def create_community(body: CommunityInput, request: Request, db: AsyncSession = Depends(get_db),
                           user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "community-create", str(user.id))
    actor = await db.scalar(select(User.id).where(User.id == user.id).with_for_update(read=True, key_share=True))
    if actor is None:
        raise HTTPException(401, "Account no longer exists")
    community = Community(**body.model_dump(), owner_id=user.id)
    db.add(community)
    try:
        await db.flush()
        db.add(CommunityMember(community_id=community.id, user_id=user.id))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Community slug already exists") from None
    await db.refresh(community)
    return (await community_responses(db, [community], user.id))[0]


@router.get("/communities/{slug}", response_model=CommunityResponse)
async def get_community(slug: str, db: AsyncSession = Depends(get_db),
                        user: User | None = Depends(get_optional_user)):
    community = await visible(db, Community, slug, user)
    return (await community_responses(db, [community], user.id if user else None))[0]


@router.patch("/communities/{slug}", response_model=CommunityResponse)
async def patch_community(slug: str, body: CommunityPatch, db: AsyncSession = Depends(get_db),
                          user: User = Depends(get_current_user)):
    community = await owned(db, Community, slug, user.id, lock=True)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(community, key, value)
    await db.commit()
    await db.refresh(community)
    return (await community_responses(db, [community], user.id))[0]


@router.delete("/communities/{slug}", status_code=204)
async def delete_community(slug: str, db: AsyncSession = Depends(get_db),
                           user: User = Depends(get_current_user)):
    community = await owned(db, Community, slug, user.id, lock=True)
    keys = list(await db.scalars(select(Post.image_key).where(Post.community_id == community.id)
                                 .order_by(Post.id).with_for_update()))
    posts = (await db.scalars(select(Post).where(Post.community_id == community.id)
                              .order_by(Post.id).with_for_update())).all()
    for post in posts:
        await db.delete(post)
    await db.flush()
    key = community.cover_key
    await db.delete(community)
    await db.commit()
    from backend.media import delete_photo
    for photo_key in [key, *keys]:
        delete_photo(photo_key)


@router.get("/communities/{slug}/members", response_model=Page[MemberResponse])
async def community_members(slug: str, params: Annotated[PageParams, Query()],
                            db: AsyncSession = Depends(get_db),
                            user: User | None = Depends(get_optional_user)):
    community = await visible(db, Community, slug, user)
    scope = cursor_scope("community_members", community_id=community.id,
                         owner=user.id if user and user.id == community.owner_id and community.visibility != "public" else None)
    cursor = decode_cursor(params.cursor, scope)
    query = select(CommunityMember.id, CommunityMember.user_id, User.username,
                   User.display_name, User.avatar_key, CommunityMember.joined_at).join(
        User, User.id == CommunityMember.user_id).where(CommunityMember.community_id == community.id)
    if cursor:
        query = query.where(tuple_(CommunityMember.joined_at, CommunityMember.id) <
                            tuple_(cursor.created_at, cursor.id))
    rows = (await db.execute(query.order_by(CommunityMember.joined_at.desc(), CommunityMember.id.desc())
                             .limit(params.limit + 1))).all()
    selected, more = rows[:params.limit], len(rows) > params.limit
    return {"items": [{"id": row.id, "user_id": row.user_id, "username": row.username,
                        "display_name": row.display_name, "role": None, "joined_at": row.joined_at,
                        "avatar_url": f"/users/{row.user_id}/avatar" if row.avatar_key else None}
                       for row in selected],
            "has_more": more,
            "next_cursor": encode_cursor(selected[-1].joined_at, selected[-1].id, scope) if more else None}


@router.put("/communities/{slug}/membership", status_code=204)
async def join_community(slug: str, db: AsyncSession = Depends(get_db),
                         user: User = Depends(get_current_user)):
    await lock_actor(db, user.id)
    community = await visible(db, Community, slug, user, lock=True)
    if community.visibility != "public":
        raise HTTPException(404, "Community not found")
    await db.execute(insert(CommunityMember).values(community_id=community.id, user_id=user.id)
                     .on_conflict_do_nothing(index_elements=["community_id", "user_id"]))
    await db.commit()


@router.get("/communities/{slug}/membership")
async def get_community_membership(slug: str, db: AsyncSession = Depends(get_db),
                                   user: User = Depends(get_current_user)):
    community = await visible(db, Community, slug, user)
    member = await db.scalar(select(CommunityMember.id).where(
        CommunityMember.community_id == community.id, CommunityMember.user_id == user.id))
    return {"is_member": member is not None, "is_owner": community.owner_id == user.id}


@router.delete("/communities/{slug}/membership", status_code=204)
async def leave_community(slug: str, db: AsyncSession = Depends(get_db),
                          user: User = Depends(get_current_user)):
    await lock_actor(db, user.id)
    community = await visible(db, Community, slug, user, lock=True)
    if community.owner_id == user.id:
        raise HTTPException(409, "Community owner cannot leave")
    await db.execute(select(CommunityMember.id).where(
        CommunityMember.community_id == community.id, CommunityMember.user_id == user.id).with_for_update())
    await db.execute(CommunityMember.__table__.delete().where(
        CommunityMember.community_id == community.id, CommunityMember.user_id == user.id))
    await db.commit()


@router.get("/communities/{slug}/posts", response_model=Page[dict])
async def list_community_posts(slug: str, params: Annotated[PageParams, Query()],
                               db: AsyncSession = Depends(get_db),
                               user: User | None = Depends(get_optional_user)):
    community = await visible(db, Community, slug, user)
    scope = cursor_scope("community_posts", community_id=community.id)
    cursor = decode_cursor(params.cursor, scope)
    query = select(Post, User.username).join(User, User.id == Post.author_id).where(
        Post.community_id == community.id, public_post())
    rows = (await db.execute(seek_page(query, Post, cursor, params.limit))).all()
    page = joined_page(rows, params.limit, scope)
    page["items"] = [{**PostResponse.model_validate(row[0]).model_dump(), "author_username": row[1]}
                     for row in page["items"]]
    return page


async def community_engagement(db, community, user_id, changes=None):
    row = await db.scalar(select(CommunityEngagement).where(
        CommunityEngagement.community_id == community.id, CommunityEngagement.user_id == user_id)
        .execution_options(populate_existing=True).with_for_update())
    if changes is not None:
        saved = changes.get("saved", row.saved if row else False)
        await db.execute(insert(CommunityEngagement).values(community_id=community.id,
            user_id=user_id, saved=saved).on_conflict_do_update(
                index_elements=["community_id", "user_id"], set_={"saved": saved}))
        await db.commit()
        return {"saved": saved}
    return {"saved": row.saved if row else False}


@router.get("/communities/{slug}/engagement")
async def get_community_engagement(slug: str, db: AsyncSession = Depends(get_db),
                                   user: User = Depends(get_current_user)):
    community = await visible(db, Community, slug, user)
    return await community_engagement(db, community, user.id)


@router.patch("/communities/{slug}/engagement")
async def patch_community_engagement(slug: str, body: SavePatch,
                                     request: Request,
                                     db: AsyncSession = Depends(get_db),
                                     user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "community-engagement", str(user.id))
    await lock_actor(db, user.id)
    community = await visible(db, Community, slug, user, lock=True)
    return await community_engagement(db, community, user.id, body.model_dump())


@router.get("/events", response_model=Page[EventResponse])
async def list_events(params: Annotated[EventParams, Query()],
                      db: AsyncSession = Depends(get_db),
                      user: User | None = Depends(get_optional_user)):
    filters = params.model_dump(mode="json", exclude={"cursor", "limit"})
    if params.saved is not None and user is None:
        raise HTTPException(401, "Sign in to filter saved events")
    scope = cursor_scope("events", user_id=user.id if user else None, **filters)
    cursor = decode_cursor(params.cursor, scope)
    query = select(Event).where(or_(Event.visibility == "public",
        Event.owner_id == (user.id if user else -1)))
    if params.saved is not None:
        query = query.outerjoin(EventEngagement, (EventEngagement.event_id == Event.id)
            & (EventEngagement.user_id == user.id)).where(
                func.coalesce(EventEngagement.saved, False).is_(params.saved))
    if params.search:
        terms = func.websearch_to_tsquery("pg_catalog.simple", params.search.strip())
        labels = _search_labels(params.search)
        query = query.where(or_(Event.search_vector.bool_op("@@")(terms),
                                Event.skills.overlap(labels), Event.topics.overlap(labels)))
    if params.skill:
        query = query.where(Event.skills.contains([params.skill.strip().lower()]))
    if params.topic:
        query = query.where(Event.topics.contains([params.topic.strip().lower()]))
    if params.language:
        query = query.where(Event.languages.contains([params.language.strip().lower()]))
    if params.format:
        query = query.where(Event.format == params.format)
    if params.status:
        query = query.where(Event.status == params.status)
    elif params.upcoming:
        query = query.where(Event.status.in_(["scheduled", "active"]))
    if params.type:
        query = query.where(Event.type == params.type)
    if params.starts_after:
        query = query.where(Event.starts_at >= params.starts_after)
    if params.starts_before:
        query = query.where(Event.starts_at <= params.starts_before)
    if params.upcoming:
        now = datetime.now(timezone.utc)
        query = query.where(Event.starts_at >= now)
        if cursor:
            query = query.where(tuple_(Event.starts_at, Event.id) > tuple_(cursor.created_at, cursor.id))
        rows = (await db.scalars(query.order_by(Event.starts_at, Event.id).limit(params.limit + 1))).all()
        selected, more = rows[:params.limit], len(rows) > params.limit
        page = {"items": await event_responses(db, selected, user.id if user else None),
                "has_more": more,
                "next_cursor": encode_cursor(selected[-1].starts_at, selected[-1].id, scope) if more else None}
        return page
    rows = (await db.scalars(seek_page(query, Event, cursor, params.limit))).all()
    selected = rows[:params.limit]
    return page_response(await event_responses(db, selected, user.id if user else None),
                         len(rows) > params.limit, selected[-1] if selected else None, scope)


@router.post("/events", response_model=EventResponse, status_code=201)
async def create_event(body: EventInput, request: Request, db: AsyncSession = Depends(get_db),
                       user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "event-create", str(user.id))
    actor = await db.scalar(select(User.id).where(User.id == user.id).with_for_update(read=True, key_share=True))
    if actor is None:
        raise HTTPException(401, "Account no longer exists")
    event = Event(**body.model_dump(), owner_id=user.id,
                  canonical_url=canonical_event_url(body.source_url), source_external_id=None)
    db.add(event)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Event slug or source already exists") from None
    await db.refresh(event)
    return (await event_responses(db, [event], user.id))[0]


@router.get("/events/{slug}", response_model=EventResponse)
async def get_event(slug: str, db: AsyncSession = Depends(get_db),
                    user: User | None = Depends(get_optional_user)):
    event = await visible(db, Event, slug, user)
    return (await event_responses(db, [event], user.id if user else None))[0]


@router.patch("/events/{slug}", response_model=EventResponse)
async def patch_event(slug: str, body: EventPatch, db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    event = await owned(db, Event, slug, user.id, lock=True)
    values = body.model_dump(exclude_unset=True)
    state = {key: getattr(event, key) for key in EventInput.model_fields}
    state.update(values)
    try:
        validated = EventInput.model_validate(state)
    except ValidationError:
        raise HTTPException(422, "Invalid event details") from None
    for key, value in validated.model_dump().items():
        setattr(event, key, value)
    if "source_url" in values:
        event.canonical_url = canonical_event_url(event.source_url)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Source URL already belongs to an event") from None
    await db.refresh(event)
    return (await event_responses(db, [event], user.id))[0]


@router.delete("/events/{slug}", status_code=204)
async def delete_event(slug: str, db: AsyncSession = Depends(get_db),
                       user: User = Depends(get_current_user)):
    event = await owned(db, Event, slug, user.id, lock=True)
    key = event.cover_key
    await db.delete(event)
    await db.commit()
    from backend.media import delete_photo
    delete_photo(key)


async def event_engagement(db, event, user_id, changes=None):
    if changes is not None:
        await db.scalar(select(User.id).where(User.id == user_id).with_for_update(read=True, key_share=True))
        await db.execute(insert(EventEngagement).values(event_id=event.id, user_id=user_id)
            .on_conflict_do_nothing(constraint="uq_event_engagement_user"))
        row = await db.scalar(select(EventEngagement).where(EventEngagement.event_id == event.id,
            EventEngagement.user_id == user_id).execution_options(populate_existing=True).with_for_update())
        if changes.get("interested_visible") is True and not changes.get("interested", row.interested):
            raise HTTPException(422, "Visible interest requires interested=true")
        for key, value in changes.items():
            setattr(row, key, value)
        if not row.interested:
            row.interested_visible = False
        await db.commit()
    else:
        row = await db.scalar(select(EventEngagement).where(
            EventEngagement.event_id == event.id, EventEngagement.user_id == user_id))
    return {"saved": row.saved if row else False, "interested": row.interested if row else False,
            "interested_visible": row.interested_visible if row else False}


@router.get("/events/{slug}/engagement")
async def get_event_engagement(slug: str, db: AsyncSession = Depends(get_db),
                               user: User = Depends(get_current_user)):
    event = await visible(db, Event, slug, user)
    return await event_engagement(db, event, user.id)


@router.get("/events/{slug}/interested", response_model=Page[InterestedUser])
async def event_interested(slug: str, params: Annotated[PageParams, Query()],
                           db: AsyncSession = Depends(get_db),
                           user: User | None = Depends(get_optional_user)):
    event = await visible(db, Event, slug, user)
    scope = cursor_scope("event_interested", event_id=event.id)
    query = select(EventEngagement, User.id.label("user_id"),
                   User.username, User.display_name, User.bio, User.avatar_key).join(
        User, User.id == EventEngagement.user_id).where(
            EventEngagement.event_id == event.id, EventEngagement.interested.is_(True),
            EventEngagement.interested_visible.is_(True))
    rows = (await db.execute(seek_page(query, EventEngagement,
        decode_cursor(params.cursor, scope), params.limit))).all()
    page = joined_page(rows, params.limit, scope)
    page["items"] = [{"id": row.user_id, "username": row.username,
                      "display_name": row.display_name, "bio": row.bio,
                      "avatar_url": f"/users/{row.user_id}/avatar" if row.avatar_key else None}
                     for row in page["items"]]
    return page


@router.patch("/events/{slug}/engagement")
async def patch_event_engagement(slug: str, body: EngagementPatch,
                                 request: Request,
                                 db: AsyncSession = Depends(get_db),
                                 user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "event-engagement", str(user.id))
    await lock_actor(db, user.id)
    event = await visible(db, Event, slug, user, lock=True)
    return await event_engagement(db, event, user.id, body.model_dump(exclude_unset=True))


@router.get("/team/{slug}", response_class=HTMLResponse, include_in_schema=False)
async def team_page(slug: str, db: AsyncSession = Depends(get_db)):
    team = await visible(db, Team, slug)
    card = (await team_responses(db, [team]))[0]
    return public_page(team.title, team.summary, "team", slug,
        f'<p>{escape(team.summary)}</p><div class="prose">{escape(team.description)}</div>'
        f'<p>{card.member_count} members · {card.openings_count} open roles</p>', team.cover_url)


@router.get("/community/{slug}", response_class=HTMLResponse, include_in_schema=False)
async def community_page(slug: str, db: AsyncSession = Depends(get_db)):
    community = await visible(db, Community, slug)
    card = (await community_responses(db, [community]))[0]
    return public_page(community.title, community.summary, "community", slug,
        f'<p>{escape(community.summary)}</p><div class="prose">{escape(community.description)}</div>'
        f'<p>{card.member_count} members · {card.published_posts_count} posts</p>', community.cover_url)


@router.get("/event/{slug}", response_class=HTMLResponse, include_in_schema=False)
async def event_page(slug: str, db: AsyncSession = Depends(get_db)):
    event = await visible(db, Event, slug)
    return public_page(event.title, event.summary, "event", slug,
        f'<p>{escape(event.summary)}</p><div class="prose">{escape(event.description)}</div>'
        f'<p>{escape(event.starts_at.isoformat())} · {escape(event.timezone)}</p>', event.cover_url)


def public_page(title, description, kind, slug, body, image_url=None):
    safe_title, safe_description = escape(title), escape(description)
    app_url = escape(PUBLIC_APP_URL, quote=True)
    image = f'<meta property="og:image" content="{escape(PUBLIC_APP_URL + image_url, quote=True)}">' if image_url else ""
    cover = f'<img class="cover" src="{escape(image_url, quote=True)}" alt="">' if image_url else ""
    return HTMLResponse(f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{safe_title} · Krug</title>
<meta name="description" content="{safe_description}"><meta property="og:title" content="{safe_title}">
<meta property="og:description" content="{safe_description}"><meta property="og:type" content="website">
<meta property="og:url" content="{app_url}/{kind}/{escape(slug, quote=True)}">
{image}<style>body{{margin:0;background:#10151c;color:#e8edf5;font:16px/1.65 system-ui,sans-serif}}header,main{{max-width:900px;margin:auto;padding:24px}}a{{color:#9ecbff}}main{{margin-top:8vh}}h1{{font-size:clamp(2rem,6vw,4rem);line-height:1.1}}.prose{{white-space:pre-wrap}}.summary{{color:#b5c2d2}}.cover{{display:block;max-width:100%;max-height:480px;object-fit:cover;border-radius:12px}}</style></head>
<body><header><a href="{app_url}/app">Krug</a></header><main>{cover}<h1>{safe_title}</h1>
<p class="summary">{safe_description}</p>{body}<p><a href="{app_url}/app#/{kind}/{escape(slug, quote=True)}">Open in Krug</a></p>
</main></body></html>''', headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.get("/teams", response_model=Page[TeamResponse])
async def list_teams(params: Annotated[TeamParams, Query()], db: AsyncSession = Depends(get_db),
                     user: User | None = Depends(get_optional_user)):
    values = params.model_dump(exclude={"cursor", "limit"})
    if params.saved is not None and user is None:
        raise HTTPException(401, "Sign in to filter saved teams")
    scope = cursor_scope("teams", user_id=user.id if user else None, **values)
    cursor = decode_cursor(params.cursor, scope)
    query = select(Team).where(or_(Team.visibility == "public",
        Team.owner_id == (user.id if user else -1)))
    if params.saved is not None:
        query = query.outerjoin(TeamEngagement, (TeamEngagement.team_id == Team.id)
            & (TeamEngagement.user_id == user.id)).where(
                func.coalesce(TeamEngagement.saved, False).is_(params.saved))
    if params.search:
        terms = func.websearch_to_tsquery("pg_catalog.simple", params.search.strip())
        labels = _search_labels(params.search)
        query = query.where(or_(Team.search_vector.bool_op("@@")(terms),
                                Team.skills.overlap(labels), Team.topics.overlap(labels)))
    if params.skill:
        query = query.where(Team.skills.contains([params.skill.strip().lower()]))
    if params.topic:
        query = query.where(Team.topics.contains([params.topic.strip().lower()]))
    if params.language:
        query = query.where(Team.languages.contains([params.language.strip().lower()]))
    if params.format:
        query = query.where(Team.format == params.format)
    if params.status:
        query = query.where(Team.status == params.status)
    else:
        query = query.where(Team.status != "archived")
    if params.event_id:
        query = query.where(Team.event_id == params.event_id)
    rows = (await db.scalars(seek_page(query, Team, cursor, params.limit))).all()
    selected = rows[:params.limit]
    return page_response(await team_responses(db, selected, user.id if user else None), len(rows) > params.limit,
                         selected[-1] if selected else None, scope)


@router.post("/teams", response_model=TeamResponse, status_code=201)
async def create_team(body: TeamInput, request: Request, db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "team-create", str(user.id))
    actor = await db.scalar(select(User.id).where(User.id == user.id).with_for_update(read=True, key_share=True))
    if actor is None:
        raise HTTPException(401, "Account no longer exists")
    if body.event_id:
        event = await db.scalar(select(Event).where(Event.id == body.event_id))
        if event is None or (event.visibility != "public" and event.owner_id != user.id):
            raise HTTPException(404, "Event not found")
    team = Team(**body.model_dump(), owner_id=user.id)
    db.add(team)
    try:
        await db.flush()
        db.add(TeamMember(team_id=team.id, user_id=user.id, role="Owner"))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Team slug already exists") from None
    await db.refresh(team)
    return (await team_responses(db, [team], user.id if user else None))[0]


@router.get("/teams/{slug}", response_model=TeamResponse)
async def get_team(slug: str, db: AsyncSession = Depends(get_db),
                   user: User | None = Depends(get_optional_user)):
    team = await visible(db, Team, slug, user)
    return (await team_responses(db, [team], user.id if user else None))[0]


@router.patch("/teams/{slug}", response_model=TeamResponse)
async def patch_team(slug: str, body: TeamPatch, db: AsyncSession = Depends(get_db),
                     user: User = Depends(get_current_user)):
    team = await owned(db, Team, slug, user.id, lock=True)
    values = body.model_dump(exclude_unset=True)
    if "event_id" in values and values["event_id"] is not None:
        event = await db.scalar(select(Event).where(Event.id == values["event_id"]))
        if event is None or (event.visibility != "public" and event.owner_id != user.id):
            raise HTTPException(404, "Event not found")
    for key, value in values.items():
        setattr(team, key, value)
    await db.commit()
    await db.refresh(team)
    return (await team_responses(db, [team], user.id))[0]


@router.delete("/teams/{slug}", status_code=204)
async def delete_team(slug: str, db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    team = await owned(db, Team, slug, user.id, lock=True)
    key = team.cover_key
    await db.delete(team)
    await db.commit()
    from backend.media import delete_photo
    delete_photo(key)


@router.get("/teams/{slug}/members", response_model=Page[MemberResponse])
async def team_members(slug: str, params: Annotated[PageParams, Query()],
                       db: AsyncSession = Depends(get_db),
                       user: User | None = Depends(get_optional_user)):
    team = await visible(db, Team, slug, user)
    scope = cursor_scope("team_members", team_id=team.id,
                         owner=user.id if user and user.id == team.owner_id and team.visibility != "public" else None)
    cursor = decode_cursor(params.cursor, scope)
    query = select(TeamMember.id, TeamMember.user_id, User.username, User.display_name,
                   User.avatar_key, TeamMember.role, TeamMember.joined_at).join(
        User, User.id == TeamMember.user_id).where(TeamMember.team_id == team.id)
    if cursor:
        query = query.where(tuple_(TeamMember.joined_at, TeamMember.id) < tuple_(cursor.created_at, cursor.id))
    rows = (await db.execute(query.order_by(TeamMember.joined_at.desc(), TeamMember.id.desc()).limit(params.limit + 1))).all()
    selected, more = rows[:params.limit], len(rows) > params.limit
    return {"items": [{"id": row.id, "user_id": row.user_id, "username": row.username,
                       "display_name": row.display_name, "role": row.role,
                       "joined_at": row.joined_at,
                       "avatar_url": f"/users/{row.user_id}/avatar" if row.avatar_key else None}
                      for row in selected], "has_more": more,
            "next_cursor": encode_cursor(selected[-1].joined_at, selected[-1].id, scope) if more else None}


@router.get("/teams/{slug}/openings", response_model=Page[OpeningResponse])
async def list_team_openings(slug: str, params: Annotated[PageParams, Query()],
                             db: AsyncSession = Depends(get_db),
                             user: User | None = Depends(get_optional_user)):
    team = await visible(db, Team, slug, user)
    owner_view = user is not None and user.id == team.owner_id
    scope = cursor_scope("team_openings", team_id=team.id, owner=user.id if owner_view else None)
    cursor = decode_cursor(params.cursor, scope)
    query = select(TeamOpening).where(TeamOpening.team_id == team.id)
    if not owner_view:
        query = query.where(TeamOpening.status == "open")
    rows = (await db.scalars(seek_page(query,
                                        TeamOpening, cursor, params.limit))).all()
    return make_page(rows, params.limit, scope)


@router.post("/teams/{slug}/openings", response_model=OpeningResponse, status_code=201)
async def create_team_opening(slug: str, body: OpeningInput, db: AsyncSession = Depends(get_db),
                              user: User = Depends(get_current_user)):
    team = await owned(db, Team, slug, user.id, lock=True)
    opening = TeamOpening(team_id=team.id, **body.model_dump())
    db.add(opening)
    await db.commit()
    await db.refresh(opening)
    return opening


@router.patch("/team-openings/{opening_id}", response_model=OpeningResponse)
async def patch_team_opening(opening_id: DatabaseId, body: OpeningPatch,
                             db: AsyncSession = Depends(get_db),
                             user: User = Depends(get_current_user)):
    team_id = await db.scalar(select(TeamOpening.team_id).where(TeamOpening.id == opening_id))
    if team_id is None:
        raise HTTPException(404, "Opening not found")
    team = await db.scalar(select(Team).where(
        Team.id == team_id, Team.owner_id == user.id).with_for_update())
    if team is None:
        raise HTTPException(404, "Opening not found")
    opening = await db.scalar(select(TeamOpening).where(
        TeamOpening.id == opening_id, TeamOpening.team_id == team.id)
        .execution_options(populate_existing=True).with_for_update())
    if opening is None:
        raise HTTPException(404, "Opening not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(opening, key, value)
    await db.commit()
    await db.refresh(opening)
    return opening


@router.post("/team-openings/{opening_id}/applications", response_model=ApplicationResponse, status_code=201)
async def apply_to_team(opening_id: DatabaseId, body: ApplicationInput,
                        request: Request,
                        db: AsyncSession = Depends(get_db),
                        user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "team-application", str(user.id))
    await lock_actor(db, user.id)
    team_id = await db.scalar(select(TeamOpening.team_id).where(TeamOpening.id == opening_id))
    if team_id is None:
        raise HTTPException(404, "Opening not found")
    team = await db.scalar(select(Team).where(Team.id == team_id).with_for_update())
    if team is None:
        raise HTTPException(404, "Opening not found")
    opening = await db.scalar(select(TeamOpening).where(
        TeamOpening.id == opening_id, TeamOpening.team_id == team.id)
        .execution_options(populate_existing=True).with_for_update())
    if opening is None or team.visibility != "public" or team.status != "recruiting" or opening.status != "open":
        raise HTTPException(404, "Opening not found")
    if await db.scalar(select(TeamMember.id).where(TeamMember.team_id == opening.team_id,
                                                   TeamMember.user_id == user.id)):
        raise HTTPException(409, "Already a team member")
    application = TeamApplication(opening_id=opening.id, applicant_id=user.id, message=body.message)
    db.add(application)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Application already exists") from None
    await db.refresh(application)
    return application


@router.get("/team-applications", response_model=Page[dict])
async def my_team_applications(params: Annotated[PageParams, Query()],
                               db: AsyncSession = Depends(get_db),
                               user: User = Depends(get_current_user)):
    scope = cursor_scope("my_team_applications", user_id=user.id)
    cursor = decode_cursor(params.cursor, scope)
    query = select(TeamApplication, Team.slug, Team.title, TeamOpening.title).join(
        TeamOpening, TeamOpening.id == TeamApplication.opening_id).join(
        Team, Team.id == TeamOpening.team_id).where(TeamApplication.applicant_id == user.id)
    rows = (await db.execute(seek_page(query, TeamApplication, cursor, params.limit))).all()
    page = joined_page(rows, params.limit, scope)
    page["items"] = [{**ApplicationResponse.model_validate(row[0]).model_dump(),
                      "team_slug": row[1], "team_title": row[2], "opening_title": row[3]}
                     for row in page["items"]]
    return page


@router.get("/teams/{slug}/applications", response_model=Page[dict])
async def list_team_applications(slug: str, params: Annotated[PageParams, Query()],
                                 db: AsyncSession = Depends(get_db),
                                 user: User = Depends(get_current_user)):
    team = await owned(db, Team, slug, user.id)
    scope = cursor_scope("team_applications", team_id=team.id)
    cursor = decode_cursor(params.cursor, scope)
    query = select(TeamApplication, TeamOpening.title, User.username, User.display_name).join(
        TeamOpening, TeamOpening.id == TeamApplication.opening_id).join(
        User, User.id == TeamApplication.applicant_id).where(TeamOpening.team_id == team.id)
    rows = (await db.execute(seek_page(query, TeamApplication, cursor, params.limit))).all()
    page = joined_page(rows, params.limit, scope)
    page["items"] = [{**ApplicationResponse.model_validate(row[0]).model_dump(),
                      "opening_title": row[1], "applicant_username": row[2],
                      "applicant_display_name": row[3]} for row in page["items"]]
    return page


@router.patch("/team-applications/{application_id}", response_model=ApplicationResponse)
async def change_team_application(application_id: DatabaseId, body: ApplicationStatus,
                                  db: AsyncSession = Depends(get_db),
                                  user: User = Depends(get_current_user)):
    app = await db.scalar(select(TeamApplication).where(TeamApplication.id == application_id))
    if app is None:
        raise HTTPException(404, "Application not found")
    opening = await db.scalar(select(TeamOpening).where(TeamOpening.id == app.opening_id))
    if opening is None:
        raise HTTPException(404, "Application not found")
    owner_action = await db.scalar(select(Team.owner_id).where(Team.id == opening.team_id)) == user.id
    account_ids = sorted({user.id, app.applicant_id} if owner_action else {user.id})
    for account_id in account_ids:
        exists = await db.scalar(select(User.id).where(User.id == account_id)
                                 .with_for_update(read=True, key_share=True))
        if exists is None:
            raise HTTPException(404, "Application not found")
    team = await db.scalar(select(Team).where(Team.id == opening.team_id).with_for_update())
    if team is None:
        raise HTTPException(404, "Application not found")
    app = await db.scalar(select(TeamApplication).where(TeamApplication.id == application_id)
                          .execution_options(populate_existing=True).with_for_update())
    if app is None:
        raise HTTPException(404, "Application not found")
    owner_action = user.id == team.owner_id
    if owner_action:
        if body.status not in {"accepted", "rejected"}:
            raise HTTPException(422, "Owners can accept or reject applications")
    elif app.applicant_id == user.id and body.status == "withdrawn":
        pass
    else:
        raise HTTPException(404, "Application not found")
    if app.status != "pending":
        raise HTTPException(409, "Application is no longer pending")
    if body.status == "accepted":
        await db.execute(insert(TeamMember).values(team_id=team.id, user_id=app.applicant_id,
            role="Member").on_conflict_do_nothing(index_elements=["team_id", "user_id"]))
    app.status = body.status
    await db.commit()
    await db.refresh(app)
    return app


@router.post("/teams/{slug}/project", response_model=ProjectResponse, status_code=201)
async def transfer_team_to_project(slug: str, body: ProjectCreate,
                                   request: Request,
                                   db: AsyncSession = Depends(get_db),
                                   user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "project-create", str(user.id))
    await db.scalar(select(User.id).where(User.id == user.id).with_for_update(read=True, key_share=True))
    team = await owned(db, Team, slug, user.id, lock=True)
    if team.linked_project_id is not None:
        project = await db.get(Project, team.linked_project_id)
        if project is not None:
            return project
        raise HTTPException(409, "Team already transferred")
    if body.derived_from_project_id is not None:
        source = await db.scalar(select(Project).where(Project.id == body.derived_from_project_id,
            Project.origin == "external", Project.visibility == "public").with_for_update(read=True))
        if source is None:
            raise HTTPException(404, "Source project not found")
    project = Project(**body.model_dump(), owner_id=user.id, origin="native",
        canonical_url=None if body.derived_from_project_id else canonical_project_url(body.source_url),
        source_name=None, source_external_id=None, last_activity_at=datetime.now(timezone.utc))
    db.add(project)
    try:
        await db.flush()
        members = (await db.scalars(select(TeamMember).where(TeamMember.team_id == team.id)
                                    .order_by(TeamMember.user_id, TeamMember.id))).all()
        for member in members:
            db.add(ProjectMember(project_id=project.id, user_id=member.user_id, role=member.role,
                                 joined_at=member.joined_at))
        team.linked_project_id = project.id
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Project slug or source URL already exists") from None
    await db.refresh(project)
    return project


async def team_engagement(db, team, user_id, changes=None):
    if changes is not None:
        await lock_actor(db, user_id)
        await db.execute(insert(TeamEngagement).values(team_id=team.id, user_id=user_id)
            .on_conflict_do_nothing(constraint="uq_team_engagement_user"))
        row = await db.scalar(select(TeamEngagement).where(TeamEngagement.team_id == team.id,
            TeamEngagement.user_id == user_id).execution_options(populate_existing=True).with_for_update())
        if changes.get("interested_visible") is True and not changes.get("interested", row.interested):
            raise HTTPException(422, "Visible interest requires interested=true")
        for key, value in changes.items():
            setattr(row, key, value)
        if not row.interested:
            row.interested_visible = False
        await db.commit()
    else:
        row = await db.scalar(select(TeamEngagement).where(TeamEngagement.team_id == team.id,
            TeamEngagement.user_id == user_id))
    return {"saved": row.saved if row else False, "interested": row.interested if row else False,
            "interested_visible": row.interested_visible if row else False}


@router.get("/teams/{slug}/engagement")
async def get_team_engagement(slug: str, db: AsyncSession = Depends(get_db),
                              user: User = Depends(get_current_user)):
    team = await visible(db, Team, slug, user)
    return await team_engagement(db, team, user.id)


@router.get("/teams/{slug}/interested", response_model=Page[InterestedUser])
async def team_interested(slug: str, params: Annotated[PageParams, Query()],
                          db: AsyncSession = Depends(get_db),
                          user: User | None = Depends(get_optional_user)):
    team = await visible(db, Team, slug, user)
    scope = cursor_scope("team_interested", team_id=team.id)
    query = select(TeamEngagement, User.id.label("user_id"),
                   User.username, User.display_name, User.bio, User.avatar_key).join(
        User, User.id == TeamEngagement.user_id).where(
            TeamEngagement.team_id == team.id, TeamEngagement.interested.is_(True),
            TeamEngagement.interested_visible.is_(True))
    rows = (await db.execute(seek_page(query, TeamEngagement,
        decode_cursor(params.cursor, scope), params.limit))).all()
    page = joined_page(rows, params.limit, scope)
    page["items"] = [{"id": row.user_id, "username": row.username,
                      "display_name": row.display_name, "bio": row.bio,
                      "avatar_url": f"/users/{row.user_id}/avatar" if row.avatar_key else None}
                     for row in page["items"]]
    return page


@router.patch("/teams/{slug}/engagement")
async def patch_team_engagement(slug: str, body: EngagementPatch,
                                request: Request,
                                db: AsyncSession = Depends(get_db),
                                user: User = Depends(get_current_user)):
    await check_rate_limit(db, request, "team-engagement", str(user.id))
    await lock_actor(db, user.id)
    team = await visible(db, Team, slug, user, lock=True)
    return await team_engagement(db, team, user.id, body.model_dump(exclude_unset=True))
