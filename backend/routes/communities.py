from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Community, CommunityEngagement, CommunityMember, Post, User
from backend.pagination import cursor_scope, decode_cursor, encode_cursor, seek_page
from backend.platform_schemas import (
    CommunityInput, CommunityPatch, CommunityParams, CommunityResponse, MemberResponse, SavePatch,
)
from backend.project_access import public_post
from backend.rate_limit import check_rate_limit
from backend.routes.platform_common import (
    _search_labels, joined_page, lock_actor, owned, page_response, visible,
)
from backend.schemas import Page, PageParams, PostResponse
from backend.security import get_current_user, get_optional_user


router = APIRouter()


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
