import pytest
from sqlalchemy import func, select

from backend.models import Comment, Like, User

pytestmark = pytest.mark.asyncio


async def post(client, author, *, published=True):
    response = await client.post("/posts", headers=author["headers"], json={
        "title": "Social post", "content": "Content", "is_published": published,
    })
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_public_profile_counts_and_private_fields(client, accounts):
    author, reader = accounts
    await post(client, author)
    await post(client, author, published=False)
    assert (await client.post("/subscriptions", headers=reader["headers"],
                              json={"author_id": author["id"]})).status_code == 201
    response = await client.patch("/me/profile", headers=author["headers"], json={"bio": "Hello"})
    assert response.status_code == 200, response.text
    profile = (await client.get(f"/authors/{author['id']}")).json()
    assert profile == {"id": author["id"], "username": author["username"], "bio": "Hello", "display_name": "",
                       "posts_count": 1, "subscribers_count": 1, "subscriptions_count": 0}
    assert (await client.patch("/me/profile", headers=author["headers"],
                              json={"bio": "x" * 501})).status_code == 422
    assert (await client.patch("/me/profile", headers=author["headers"],
                              json={"bio": None})).status_code == 422
    assert (await client.patch("/me/profile", json={"bio": "No"})).status_code == 401
    assert (await client.get("/authors/2147483647")).status_code == 404


async def test_idempotent_likes_and_draft_visibility(client, accounts, db):
    author, reader = accounts
    published, draft = await post(client, author), await post(client, author, published=False)
    url = f"/posts/{published}/likes"
    assert (await client.get(url)).json() == {"count": 0, "liked": False}
    for _ in range(2):
        response = await client.put(url, headers=reader["headers"])
        assert response.status_code == 200, response.text
        assert response.json() == {"count": 1, "liked": True}
    assert (await client.get(url)).json() == {"count": 1, "liked": False}
    assert await db.scalar(select(func.count()).select_from(Like).where(Like.post_id == published)) == 1
    for _ in range(2):
        assert (await client.delete(url, headers=reader["headers"])).json() == {"count": 0, "liked": False}
    assert (await client.put(url)).status_code == 401
    for method in (client.get, client.put, client.delete):
        assert (await method(f"/posts/{draft}/likes", headers=reader["headers"])).status_code == 404
    assert (await client.get(f"/posts/{draft}/likes")).status_code == 404
    assert (await client.put(f"/posts/{draft}/likes", headers=author["headers"])).json()["liked"] is True
    await client.put(url, headers=reader["headers"])
    await client.put(f"/posts/{published}", headers=author["headers"], json={"is_published": False})
    assert (await client.get(url, headers=reader["headers"])).status_code == 404


async def test_flat_comments_pagination_and_validation(client, accounts):
    author, reader = accounts
    post_id = await post(client, author)
    url = f"/posts/{post_id}/comments"
    assert (await client.get(url)).json() == {"items": [], "next_cursor": None, "has_more": False}
    ids = []
    for text in (" first ", "second", "third"):
        response = await client.post(url, headers=reader["headers"], json={"content": text})
        assert response.status_code == 201, response.text
        comment = response.json()
        assert comment["content"] == text.strip()
        assert comment["username"] == reader["username"]
        assert set(comment) == {"id", "post_id", "user_id", "username", "content", "created_at"}
        ids.append(comment["id"])
    first = (await client.get(url, params={"limit": 2})).json()
    assert [c["id"] for c in first["items"]] == ids[::-1][:2]
    assert first["has_more"] is True
    second = (await client.get(url, params={"limit": 2, "cursor": first["next_cursor"]})).json()
    assert [c["id"] for c in second["items"]] == ids[:1]
    assert second["has_more"] is False
    other_id = await post(client, author)
    assert (await client.get(f"/posts/{other_id}/comments",
                             params={"cursor": first["next_cursor"]})).status_code == 422
    for content in ("", " \n\t", "x" * 2001, None):
        assert (await client.post(url, headers=reader["headers"], json={"content": content})).status_code == 422
    assert (await client.post(url, headers=reader["headers"],
                              json={"content": "reply", "parent_id": ids[0]})).status_code == 422
    assert (await client.post(url, json={"content": "No auth"})).status_code == 401


async def test_comment_deletion_rights_and_hidden_posts(client, accounts):
    author, reader = accounts
    post_id = await post(client, author)
    url = f"/posts/{post_id}/comments"
    own = (await client.post(url, headers=author["headers"], json={"content": "Author"})).json()["id"]
    assert (await client.delete(f"{url}/{own}", headers=reader["headers"])).status_code == 403
    foreign = (await client.post(url, headers=reader["headers"], json={"content": "Reader"})).json()["id"]
    assert (await client.delete(f"{url}/{foreign}", headers=author["headers"])).status_code == 204
    foreign = (await client.post(url, headers=reader["headers"], json={"content": "Reader"})).json()["id"]
    assert (await client.delete(f"{url}/{foreign}", headers=reader["headers"])).status_code == 204
    await client.put(f"/posts/{post_id}", headers=author["headers"], json={"is_published": False})
    assert (await client.get(url)).status_code == 404
    assert (await client.get(url, headers=reader["headers"])).status_code == 404
    assert (await client.post(url, headers=reader["headers"], json={"content": "Hidden"})).status_code == 404
    assert (await client.delete(f"{url}/{own}", headers=reader["headers"])).status_code == 404
    assert (await client.get(url, headers=author["headers"])).status_code == 200
    assert (await client.delete(f"{url}/{own}", headers=author["headers"])).status_code == 204


async def test_interactions_cascade_on_post_and_user_deletion(client, accounts, db):
    author, reader = accounts
    post_id = await post(client, author)
    await client.put(f"/posts/{post_id}/likes", headers=reader["headers"])
    await client.post(f"/posts/{post_id}/comments", headers=reader["headers"], json={"content": "Hello"})
    assert (await client.delete(f"/posts/{post_id}", headers=author["headers"])).status_code == 204
    for model in (Like, Comment):
        assert await db.scalar(select(func.count()).select_from(model).where(model.post_id == post_id)) == 0
    post_id = await post(client, author)
    await client.put(f"/posts/{post_id}/likes", headers=reader["headers"])
    await client.post(f"/posts/{post_id}/comments", headers=reader["headers"], json={"content": "Hello"})
    await db.delete(await db.get(User, reader["id"]))
    await db.commit()
    for model in (Like, Comment):
        assert await db.scalar(select(func.count()).select_from(model).where(model.post_id == post_id)) == 0


async def test_two_connections_like_once_without_conflicts():
    import asyncio
    from uuid import uuid4

    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from backend.database import ASYNC_DATABASE_URL
    from backend.models import Post
    from backend.routes.social import like_post

    engine = create_async_engine(ASYNC_DATABASE_URL, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    user_id = post_id = None
    ready, start = asyncio.Queue(), asyncio.Event()
    tasks = []
    try:
        async with sessions() as seed:
            user = User(username=f"like_race_{uuid4().hex}", hashed_password="unused")
            seed.add(user)
            await seed.flush()
            user_id = user.id
            item = Post(author_id=user_id, title="Race", content="Body", is_published=True)
            seed.add(item)
            await seed.commit()
            post_id = item.id

        async def like_once():
            async with sessions() as session:
                user = await session.get(User, user_id)
                await ready.put(None)
                await start.wait()
                return await like_post(post_id, db=session, user=user)

        tasks = [asyncio.create_task(like_once()) for _ in range(2)]
        await asyncio.wait_for(ready.get(), timeout=5)
        await asyncio.wait_for(ready.get(), timeout=5)
        start.set()
        results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=5)
        assert results == [{"count": 1, "liked": True}] * 2
        async with sessions() as check:
            assert await check.scalar(select(func.count()).select_from(Like).where(Like.post_id == post_id)) == 1
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        try:
            async with sessions() as cleanup:
                if post_id is not None:
                    await cleanup.execute(delete(Post).where(Post.id == post_id))
                if user_id is not None:
                    await cleanup.execute(delete(User).where(User.id == user_id))
                await cleanup.commit()
        finally:
            await engine.dispose()


async def test_account_deletion_blocks_new_posts_and_preserves_other_photos(monkeypatch, tmp_path):
    import asyncio
    from uuid import uuid4

    from sqlalchemy import delete, text
    from sqlalchemy.exc import DBAPIError, IntegrityError
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from backend.crud.users import delete_user
    from backend.database import ASYNC_DATABASE_URL
    from backend.models import Post

    monkeypatch.setattr("backend.media.MEDIA_ROOT", tmp_path)
    collecting, proceed = asyncio.Event(), asyncio.Event()

    class DeletionSession(AsyncSession):
        async def scalars(self, statement, *args, **kwargs):
            collecting.set()
            await proceed.wait()
            return await super().scalars(statement, *args, **kwargs)

    engine = create_async_engine(ASYNC_DATABASE_URL, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    deletion_sessions = async_sessionmaker(engine, class_=DeletionSession, expire_on_commit=False)
    user_ids, post_ids = [], []
    keys = [f"{uuid4().hex}.jpg" for _ in range(2)]
    task = None
    try:
        async with sessions() as seed:
            for key in keys:
                user = User(username=f"delete_race_{uuid4().hex}", hashed_password="unused")
                seed.add(user)
                await seed.flush()
                user_ids.append(user.id)
                item = Post(author_id=user.id, title="Photo", content="Body", image_key=key)
                seed.add(item)
                await seed.flush()
                post_ids.append(item.id)
                (tmp_path / key).write_bytes(b"temporary photo")
            await seed.commit()

        async with deletion_sessions() as deleting, sessions() as creating:
            task = asyncio.create_task(delete_user(deleting, user_ids[0]))
            await asyncio.wait_for(collecting.wait(), timeout=5)
            # PostgreSQL must actually wait on the account lock, not merely run slowly.
            await creating.execute(text("SET LOCAL lock_timeout = '200ms'"))
            creating.add(Post(author_id=user_ids[0], title="Concurrent", content="Body"))
            with pytest.raises(DBAPIError) as blocked:
                await creating.flush()
            assert blocked.value.orig.sqlstate == "55P03"
            await creating.rollback()
            proceed.set()
            assert await asyncio.wait_for(task, timeout=5) is True
            creating.add(Post(author_id=user_ids[0], title="Deleted author", content="Body"))
            with pytest.raises(IntegrityError) as missing_author:
                await creating.flush()
            assert missing_author.value.orig.sqlstate == "23503"
            await creating.rollback()
            assert await creating.get(User, user_ids[0]) is None
            assert await creating.get(Post, post_ids[0]) is None
            assert await creating.get(Post, post_ids[1]) is not None
        assert not (tmp_path / keys[0]).exists()
        assert (tmp_path / keys[1]).read_bytes() == b"temporary photo"
    finally:
        proceed.set()
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        try:
            async with sessions() as cleanup:
                await cleanup.execute(delete(Post).where(Post.id.in_(post_ids)))
                await cleanup.execute(delete(User).where(User.id.in_(user_ids)))
                await cleanup.commit()
        finally:
            await engine.dispose()
