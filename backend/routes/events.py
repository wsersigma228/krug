from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Event, EventEngagement, User
from backend.pagination import cursor_scope, decode_cursor, encode_cursor, seek_page
from backend.platform_schemas import (
    EngagementPatch, EventInput, EventParams, EventPatch, EventResponse,
)
from backend.project_schemas import InterestedUser
from backend.rate_limit import check_rate_limit
from backend.routes.platform_common import (
    _search_labels, joined_page, lock_actor, owned, page_response, visible,
)
from backend.schemas import Page, PageParams
from backend.security import get_current_user, get_optional_user


router = APIRouter()


def canonical_event_url(url):
    if url is None:
        return None
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, ""))


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
