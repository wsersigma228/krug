from fastapi import HTTPException
from sqlalchemy import select

from backend.models import User
from backend.pagination import encode_cursor


def _search_labels(search: str) -> list[str]:
    value = search.strip().lower()
    if value in {"game dev", "gamedev", "game development", "game-development"}:
        return ["game dev", "gamedev", "game development", "game-development"]
    return [value]


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


def joined_page(rows, limit, scope):
    items = rows[:limit]
    more = len(rows) > limit
    last = items[-1][0] if more else None
    return {"items": items, "has_more": more,
            "next_cursor": encode_cursor(last.created_at, last.id, scope) if more else None}
