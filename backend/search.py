"""Full-text search with a cursor matching relevance order."""
from sqlalchemy import Float, cast, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.models import Post
from backend.pagination import Cursor, encode_cursor


def search_statement(
    user_id: int | None, search: str, language: str,
    is_published: bool | None = None, limit: int = 100, cursor: Cursor | None = None,
):
    vectors = {
        "simple": Post.search_simple,
        "russian": Post.search_russian,
        "english": Post.search_english,
    }
    vector = vectors[language]
    terms = func.websearch_to_tsquery(f"pg_catalog.{language}", search)
    # Use double precision on both pages to preserve the cursor boundary.
    rank = cast(func.ts_rank(vector, terms), Float(53))
    query = select(Post, rank.label("rank")).where(
        vector.bool_op("@@")(terms),
    )
    if user_id is None:
        query = query.where(Post.is_published.is_(True)).options(joinedload(Post.author))
    else:
        query = query.where(Post.author_id == user_id)
    if is_published is not None:
        query = query.where(Post.is_published.is_(is_published))
    if cursor is not None:
        query = query.where(
            tuple_(rank, Post.created_at, Post.id)
            < tuple_(cursor.rank, cursor.created_at, cursor.id)
        )
    return query.order_by(rank.desc(), Post.created_at.desc(), Post.id.desc()).limit(limit + 1)


async def search_posts(
    db: AsyncSession, user_id: int | None, search: str, language: str,
    is_published: bool | None, limit: int, cursor: Cursor | None, scope: str,
):
    rows = (await db.execute(search_statement(
        user_id, search, language, is_published, limit, cursor,
    ))).all()
    items = rows[:limit]
    has_more = len(rows) > limit
    next_cursor = None
    if has_more:
        post, rank = items[-1]
        next_cursor = encode_cursor(post.created_at, post.id, scope, rank=rank)
    return {
        "items": [post for post, rank in items],
        "next_cursor": next_cursor,
        "has_more": has_more,
    }
