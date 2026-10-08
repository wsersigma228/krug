from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from backend.config import MEDIA_ROOT
from backend.database import get_db
from backend.project_access import public_post
from backend.media import MAX_UPLOAD_BYTES, delete_photo, save_photo
from backend.models import Community, CommunityMember, Event, Post, Project, Team, User
from backend.schemas import PostResponse
from backend.security import get_current_user, get_optional_user

router = APIRouter()


async def owned_post(db, post_id, user_id):
    actor = await db.scalar(select(User.id).where(User.id == user_id)
                            .with_for_update(read=True, key_share=True))
    if actor is None:
        raise HTTPException(401, "Account no longer exists")
    community_id = await db.scalar(select(Post.community_id).where(
        Post.id == post_id, Post.author_id == user_id))
    if community_id is not None:
        community = await db.scalar(select(Community).where(Community.id == community_id)
                                    .execution_options(populate_existing=True).with_for_update())
        if community is None:
            raise HTTPException(404, "Post not found")
        member = await db.scalar(select(CommunityMember.id).where(
            CommunityMember.community_id == community_id, CommunityMember.user_id == user_id))
        if member is None:
            raise HTTPException(403, "Join the community before editing its posts")
    post = await db.scalar(select(Post).where(Post.id == post_id, Post.author_id == user_id)
                           .execution_options(populate_existing=True).with_for_update())
    if not post:
        raise HTTPException(404, "Post not found")
    return post


@router.put("/posts/{post_id}/image", response_model=PostResponse)
async def upload_image(post_id: int, request: Request, db: AsyncSession = Depends(get_db),
                       user: User = Depends(get_current_user)):
    """Send the image as the raw request body (not multipart)."""
    post = await owned_post(db, post_id, user.id)
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Image must be at most 8 MiB")
    key = await run_in_threadpool(save_photo, bytes(data))
    old_key = post.image_key
    post.image_key = key
    try:
        await db.commit()
    except Exception:
        delete_photo(key)
        raise
    delete_photo(old_key)
    await db.refresh(post)
    return post


@router.delete("/posts/{post_id}/image", status_code=204)
async def remove_image(post_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    post = await owned_post(db, post_id, user.id)
    old_key = post.image_key
    post.image_key = None
    await db.commit()
    delete_photo(old_key)


@router.get("/posts/{post_id}/image")
async def read_image(post_id: int, db: AsyncSession = Depends(get_db), user: User | None = Depends(get_optional_user)):
    post = await db.scalar(select(Post).where(
        Post.id == post_id, or_(public_post(), Post.author_id == (user.id if user else -1))))
    if not post or not post.image_key:
        raise HTTPException(404, "Image not found")
    try:
        data = await run_in_threadpool((MEDIA_ROOT / post.image_key).read_bytes)
    except FileNotFoundError:
        raise HTTPException(404, "Image not found") from None
    return Response(data, media_type="image/jpeg", headers={
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    })


async def replace_cover(kind, slug, request, db, user):
    model = {"projects": Project, "teams": Team, "communities": Community, "events": Event}[kind]
    await db.scalar(select(User.id).where(User.id == user.id).with_for_update(read=True, key_share=True))
    entity = await db.scalar(select(model).where(model.slug == slug, model.owner_id == user.id)
                             .execution_options(populate_existing=True).with_for_update())
    if entity is None:
        raise HTTPException(404, "Entity not found")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Image must be at most 8 MiB")
    key = await run_in_threadpool(save_photo, bytes(data))
    old_key = entity.cover_key
    entity.cover_key = key
    try:
        await db.commit()
    except Exception:
        delete_photo(key)
        raise
    delete_photo(old_key)
    return {"cover_url": entity.cover_url}


async def remove_cover(kind, slug, db, user):
    model = {"projects": Project, "teams": Team, "communities": Community, "events": Event}[kind]
    await db.scalar(select(User.id).where(User.id == user.id).with_for_update(read=True, key_share=True))
    entity = await db.scalar(select(model).where(model.slug == slug, model.owner_id == user.id)
                             .execution_options(populate_existing=True).with_for_update())
    if entity is None:
        raise HTTPException(404, "Entity not found")
    key = entity.cover_key
    entity.cover_key = None
    await db.commit()
    delete_photo(key)


async def read_cover(kind, slug, db, user):
    model = {"projects": Project, "teams": Team, "communities": Community, "events": Event}[kind]
    entity = await db.scalar(select(model).where(model.slug == slug))
    if entity is None or not entity.cover_key or (
        entity.visibility != "public" and (user is None or entity.owner_id != user.id)
    ):
        raise HTTPException(404, "Cover not found")
    try:
        data = await run_in_threadpool((MEDIA_ROOT / entity.cover_key).read_bytes)
    except FileNotFoundError:
        raise HTTPException(404, "Cover not found") from None
    return Response(data, media_type="image/jpeg", headers={
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    })


def register_cover_routes(kind):
    async def upload(slug: str, request: Request, db: AsyncSession = Depends(get_db),
                     user: User = Depends(get_current_user)):
        return await replace_cover(kind, slug, request, db, user)

    async def remove(slug: str, db: AsyncSession = Depends(get_db),
                     user: User = Depends(get_current_user)):
        await remove_cover(kind, slug, db, user)
        return Response(status_code=204)

    async def read(slug: str, db: AsyncSession = Depends(get_db),
                   user: User | None = Depends(get_optional_user)):
        return await read_cover(kind, slug, db, user)

    router.add_api_route(f"/{kind}/{{slug}}/cover", upload, methods=["PUT"],
                         name=f"upload_{kind}_cover")
    router.add_api_route(f"/{kind}/{{slug}}/cover", remove, methods=["DELETE"],
                         name=f"delete_{kind}_cover", status_code=204)
    router.add_api_route(f"/{kind}/{{slug}}/cover", read, methods=["GET"],
                         name=f"read_{kind}_cover")


for _kind in ("projects", "teams", "communities", "events"):
    register_cover_routes(_kind)


@router.put("/me/avatar")
async def upload_avatar(request: Request, db: AsyncSession = Depends(get_db),
                        user: User = Depends(get_current_user)):
    actor = await db.scalar(select(User).where(User.id == user.id).execution_options(
        populate_existing=True).with_for_update())
    if actor is None:
        raise HTTPException(401, "Account no longer exists")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Image must be at most 8 MiB")
    key = await run_in_threadpool(save_photo, bytes(data))
    old_key = actor.avatar_key
    actor.avatar_key = key
    try:
        await db.commit()
    except Exception:
        delete_photo(key)
        raise
    delete_photo(old_key)
    return {"avatar_url": actor.avatar_url}


@router.delete("/me/avatar", status_code=204)
async def delete_avatar(db: AsyncSession = Depends(get_db),
                        user: User = Depends(get_current_user)):
    actor = await db.scalar(select(User).where(User.id == user.id).execution_options(
        populate_existing=True).with_for_update())
    if actor is None:
        raise HTTPException(401, "Account no longer exists")
    key = actor.avatar_key
    actor.avatar_key = None
    await db.commit()
    delete_photo(key)


@router.get("/users/{user_id}/avatar")
async def get_avatar(user_id: int, db: AsyncSession = Depends(get_db)):
    key = await db.scalar(select(User.avatar_key).where(User.id == user_id))
    if not key:
        raise HTTPException(404, "Avatar not found")
    try:
        data = await run_in_threadpool((MEDIA_ROOT / key).read_bytes)
    except FileNotFoundError:
        raise HTTPException(404, "Avatar not found") from None
    return Response(data, media_type="image/jpeg", headers={
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    })
