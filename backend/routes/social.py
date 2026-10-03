from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Comment, Like, Post, Subscription, User
from backend.pagination import cursor_scope, decode_cursor, make_page, seek_page
from backend.schemas import Page, PageParams
from backend.security import get_current_user, get_optional_user

router = APIRouter()


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bio: str = Field(max_length=500)


class ProfileResponse(BaseModel):
    id: int
    username: str
    bio: str
    posts_count: int
    subscribers_count: int
    subscriptions_count: int


class LikesResponse(BaseModel):
    count: int
    liked: bool


class CommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def trim_content(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Comment cannot be blank")
        return value


class CommentResponse(BaseModel):
    id: int
    post_id: int
    user_id: int
    username: str
    content: str
    created_at: datetime


async def visible_post(db, post_id, user, *, lock=False):
    query = select(Post).where(Post.id == post_id).execution_options(populate_existing=True)
    if lock:
        # Match account deletion's User -> Post order; FK writes also need this user.
        actor = await db.scalar(select(User.id).where(User.id == user.id)
                                .with_for_update(read=True, key_share=True))
        if actor is None:
            raise HTTPException(401, "Account no longer exists")
        # Serialize interactions with hiding/deleting the post, then check fresh visibility.
        query = query.with_for_update()
    post = await db.scalar(query)
    if post is None or (not post.is_published and (user is None or post.author_id != user.id)):
        raise HTTPException(status_code=404, detail="Post not found")
    return post


async def profile(db, author_id):
    author = await db.get(User, author_id)
    if author is None:
        raise HTTPException(status_code=404, detail="Author not found")
    return {
        "id": author.id, "username": author.username, "bio": author.bio,
        "posts_count": await db.scalar(select(func.count()).select_from(Post).where(
            Post.author_id == author.id, Post.is_published.is_(True))),
        "subscribers_count": await db.scalar(select(func.count()).select_from(Subscription).where(
            Subscription.author_id == author.id)),
        "subscriptions_count": await db.scalar(select(func.count()).select_from(Subscription).where(
            Subscription.subscriber_id == author.id)),
    }


@router.get("/authors/{author_id}", response_model=ProfileResponse)
async def get_profile(author_id: int, db: AsyncSession = Depends(get_db)):
    """Public profile; counts include published posts only and never expose email."""
    return await profile(db, author_id)


@router.patch("/me/profile", response_model=ProfileResponse)
async def update_profile(body: ProfileUpdate, db: AsyncSession = Depends(get_db),
                         user: User = Depends(get_current_user)):
    await db.execute(update(User).where(User.id == user.id).values(bio=body.bio))
    await db.commit()
    return await profile(db, user.id)


async def likes(db, post_id, user):
    count = await db.scalar(select(func.count()).select_from(Like).where(Like.post_id == post_id))
    liked = user is not None and await db.get(Like, (post_id, user.id)) is not None
    return {"count": count, "liked": liked}


@router.get("/posts/{post_id}/likes", response_model=LikesResponse)
async def get_likes(post_id: int, db: AsyncSession = Depends(get_db),
                    user: User | None = Depends(get_optional_user)):
    await visible_post(db, post_id, user)
    return await likes(db, post_id, user)


@router.put("/posts/{post_id}/likes", response_model=LikesResponse)
async def like_post(post_id: int, db: AsyncSession = Depends(get_db),
                    user: User = Depends(get_current_user)):
    await visible_post(db, post_id, user, lock=True)
    await db.execute(insert(Like).values(post_id=post_id, user_id=user.id).on_conflict_do_nothing())
    result = await likes(db, post_id, user)
    await db.commit()
    return result


@router.delete("/posts/{post_id}/likes", response_model=LikesResponse)
async def unlike_post(post_id: int, db: AsyncSession = Depends(get_db),
                      user: User = Depends(get_current_user)):
    await visible_post(db, post_id, user, lock=True)
    await db.execute(delete(Like).where(Like.post_id == post_id, Like.user_id == user.id))
    result = await likes(db, post_id, user)
    await db.commit()
    return result


@router.get("/posts/{post_id}/comments", response_model=Page[CommentResponse])
async def get_comments(post_id: int, params: Annotated[PageParams, Query()],
                       db: AsyncSession = Depends(get_db),
                       user: User | None = Depends(get_optional_user)):
    await visible_post(db, post_id, user)
    scope = cursor_scope("comments", post_id=post_id)
    cursor = decode_cursor(params.cursor, scope)
    query = select(Comment.id, Comment.post_id, Comment.user_id, User.username,
                   Comment.content, Comment.created_at).join(User, User.id == Comment.user_id)
    rows = (await db.execute(seek_page(query.where(Comment.post_id == post_id),
                                     Comment, cursor, params.limit))).all()
    page = make_page(rows, params.limit, scope)
    page["items"] = [dict(row._mapping) for row in page["items"]]
    return page


@router.post("/posts/{post_id}/comments", response_model=CommentResponse, status_code=201)
async def create_comment(post_id: int, body: CommentCreate,
                         db: AsyncSession = Depends(get_db),
                         user: User = Depends(get_current_user)):
    await visible_post(db, post_id, user, lock=True)
    comment = Comment(post_id=post_id, user_id=user.id, content=body.content)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return {"id": comment.id, "post_id": comment.post_id, "user_id": comment.user_id,
            "username": user.username, "content": comment.content, "created_at": comment.created_at}


@router.delete("/posts/{post_id}/comments/{comment_id}", status_code=204)
async def delete_comment(post_id: int, comment_id: int,
                         db: AsyncSession = Depends(get_db),
                         user: User = Depends(get_current_user)):
    post = await visible_post(db, post_id, user, lock=True)
    comment = await db.scalar(select(Comment).where(Comment.id == comment_id, Comment.post_id == post_id))
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if user.id not in (comment.user_id, post.author_id):
        raise HTTPException(status_code=403, detail="Cannot delete this comment")
    await db.delete(comment)
    await db.commit()
