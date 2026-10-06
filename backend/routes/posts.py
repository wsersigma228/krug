from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    PostCreate,
    PostUpdate,
    PostResponse,
    FeedPostResponse,
    SubscribeRequest,
    SubscriptionResponse,
    AuthorWithSubscriptionResponse,
    Page,
    PageParams,
    PostPageParams,
    ExploreParams,
)
from backend.pagination import cursor_scope, decode_cursor, make_page
from backend.search import search_posts
from backend.project_access import public_post
from backend.security import get_current_user, get_optional_user
from backend.crud import posts as crud_posts
from backend.crud import subscriptions as crud_subs
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from backend.models import Post
from backend.pagination import seek_page

router = APIRouter()


@router.get("/explore", response_model=Page[FeedPostResponse])
async def explore(params: Annotated[ExploreParams, Query()], db: AsyncSession = Depends(get_db)):
    """Public chronological posts or ranked full-text search across published posts."""
    search = (params.search or "").strip() or None
    scope = cursor_scope("explore", search=search, language=params.search_language)
    cursor = decode_cursor(params.cursor, scope, ranked=bool(search))
    if search:
        page = await search_posts(db, None, search, params.search_language, True,
                                  params.limit, cursor, scope)
    else:
        rows = (await db.scalars(seek_page(
            select(Post).where(public_post()).options(joinedload(Post.author)),
            Post, cursor, params.limit))).all()
        page = make_page(rows, params.limit, scope)
    page["items"] = [
        {**PostResponse.model_validate(post).model_dump(), "author_username": post.author.username}
        for post in page["items"]
    ]
    return page


@router.post("/posts", response_model=PostResponse, status_code=201)
async def create_post(
    post_data: PostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a draft or publish a post and notify subscribers."""
    post = await crud_posts.create_post(db=db, post_data=post_data, author_id=current_user.id)

    return post


@router.get("/posts", response_model=Page[PostResponse])
async def get_my_posts(
    params: Annotated[PostPageParams, Query()],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Page through your posts, with optional ranked full-text search."""
    search = (params.search or "").strip() or None
    if search:
        scope = cursor_scope(
            "posts_search_v1", user_id=current_user.id,
            is_published=params.is_published, search=search,
            language=params.search_language,
        )
        cursor = decode_cursor(params.cursor, scope, ranked=True)
        return await search_posts(
            db=db, user_id=current_user.id, search=search, language=params.search_language,
            is_published=params.is_published, limit=params.limit, cursor=cursor, scope=scope,
        )
    scope = cursor_scope(
        "posts",
        user_id=current_user.id,
        is_published=params.is_published,
        search=None,
    )
    cursor = decode_cursor(params.cursor, scope)
    posts = await crud_posts.get_user_posts(
        db=db,
        user_id=current_user.id,
        is_published=params.is_published,
        limit=params.limit,
        cursor=cursor,
    )
    return make_page(posts, params.limit, scope)


@router.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Only the author can read a draft."""
    post = None
    if current_user:
        post = await crud_posts.get_post(db, post_id, user_id=current_user.id)
    if not post:
        post = await crud_posts.get_published_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.put("/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    post_data: PostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an owned post; notify only when it becomes published."""
    result = await crud_posts.update_post(
        db=db, post_id=post_id, user_id=current_user.id, post_data=post_data
    )
    if not result:
        raise HTTPException(status_code=404, detail="Post not found")
    post, _ = result
    return post


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an owned post."""
    success = await crud_posts.delete_post(db, post_id=post_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Post not found")
    return None


@router.get("/feed", response_model=Page[FeedPostResponse])
async def get_feed(
    params: Annotated[PageParams, Query()],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Page through published posts from followed authors, newest first."""
    scope = cursor_scope("feed", user_id=current_user.id)
    cursor = decode_cursor(params.cursor, scope)
    posts = await crud_posts.get_feed(
        db=db, user_id=current_user.id, limit=params.limit, cursor=cursor
    )
    page = make_page(posts, params.limit, scope)

    page["items"] = [
        FeedPostResponse(
            id=p.id,
            project_id=p.project_id,
            title=p.title,
            content=p.content,
            is_published=p.is_published,
            author_id=p.author_id,
            created_at=p.created_at,
            updated_at=p.updated_at,
            image_url=p.image_url,
            author_username=p.author.username,
        )
        for p in page["items"]
    ]
    return Page[FeedPostResponse].model_validate(page)


@router.get("/authors/{author_id}/posts", response_model=Page[PostResponse])
async def get_author_posts(
    author_id: int,
    params: Annotated[PageParams, Query()],
    db: AsyncSession = Depends(get_db),
):
    """Page through an author's published posts without signing in."""
    scope = cursor_scope("author_posts", author_id=author_id)
    cursor = decode_cursor(params.cursor, scope)
    posts = await crud_posts.get_user_posts(
        db=db, user_id=author_id, is_published=True, limit=params.limit, cursor=cursor, public_only=True
    )
    return make_page(posts, params.limit, scope)


@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=201)
async def subscribe_to_author(
    body: SubscribeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Subscribe to an author. Cannot self-subscribe or subscribe twice."""
    sub = await crud_subs.subscribe(db=db, subscriber_id=current_user.id, author_id=body.author_id)
    if not sub:
        raise HTTPException(status_code=400, detail="Cannot subscribe (self-subscribe, already subscribed, or author not found)")
    return sub


@router.delete("/subscriptions/{author_id}", status_code=204)
async def unsubscribe_from_author(
    author_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unsubscribe from an author."""
    success = await crud_subs.unsubscribe(db=db, subscriber_id=current_user.id, author_id=author_id)
    if not success:
        raise HTTPException(status_code=404, detail="Not subscribed to this author")
    return None


@router.get("/subscriptions", response_model=Page[AuthorWithSubscriptionResponse])
async def get_my_subscriptions(
    params: Annotated[PageParams, Query()],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List followed authors, newest subscription first."""
    scope = cursor_scope("subscriptions", user_id=current_user.id)
    cursor = decode_cursor(params.cursor, scope)
    rows = await crud_subs.get_subscription_page(
        db, current_user.id, limit=params.limit, cursor=cursor
    )
    page = make_page(rows, params.limit, scope)
    page["items"] = [row.author for row in page["items"]]
    return page


@router.get("/subscribers", response_model=Page[AuthorWithSubscriptionResponse])
async def get_my_subscribers(
    params: Annotated[PageParams, Query()],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List subscribers, newest subscription first."""
    scope = cursor_scope("subscribers", user_id=current_user.id)
    cursor = decode_cursor(params.cursor, scope)
    rows = await crud_subs.get_subscription_page(
        db, current_user.id, followers=True, limit=params.limit, cursor=cursor
    )
    page = make_page(rows, params.limit, scope)
    page["items"] = [row.subscriber for row in page["items"]]
    return page


@router.get("/subscriptions/{author_id}/check", response_model=dict)
async def check_subscription(
    author_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check whether you follow this author."""
    subscribed = await crud_subs.is_subscribed(
        db=db, subscriber_id=current_user.id, author_id=author_id
    )
    return {"subscribed": subscribed}
