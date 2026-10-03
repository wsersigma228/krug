from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from backend.config import MEDIA_ROOT
from backend.database import get_db
from backend.media import MAX_UPLOAD_BYTES, delete_photo, save_photo
from backend.models import Post, User
from backend.schemas import PostResponse
from backend.security import get_current_user, get_optional_user

router = APIRouter()


async def owned_post(db, post_id, user_id):
    actor = await db.scalar(select(User.id).where(User.id == user_id)
                            .with_for_update(read=True, key_share=True))
    if actor is None:
        raise HTTPException(401, "Account no longer exists")
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
        Post.id == post_id, or_(Post.is_published.is_(True), Post.author_id == (user.id if user else -1))))
    if not post or not post.image_key:
        raise HTTPException(404, "Image not found")
    try:
        data = await run_in_threadpool((MEDIA_ROOT / post.image_key).read_bytes)
    except FileNotFoundError:
        raise HTTPException(404, "Image not found") from None
    return Response(data, media_type="image/jpeg", headers={
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    })
