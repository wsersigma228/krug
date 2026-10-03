from unittest.mock import Mock

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from backend.models import EmailDelivery, Post, Subscription, User
from backend.crud import posts as crud_posts
from backend.schemas import PostCreate
from backend.tasks.celery_app import celery_app
from backend.security import create_access_token, create_refresh_token


async def create_post(client, author, **fields):
    response = await client.post("/posts", headers=author["headers"], json={
        "title": "First post", "content": "Some content", **fields,
    })
    assert response.status_code == 201, response.text
    return response.json()


async def enable_publication_emails(client, db, account):
    user = await db.get(User, account["id"])
    user.email_verified = True
    await db.commit()
    assert (await client.patch("/me/notifications", headers=account["headers"], json={
        "email_publications": True,
    })).status_code == 200


async def test_login_and_token_types(client, accounts):
    author, _ = accounts
    unknown = await client.post("/login", json={"username": "missing-account", "password": "wrong"})
    wrong = await client.post("/login", json={"username": author["username"], "password": "wrong"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json() == {"detail": "Invalid username or password"}
    assert (await client.get("/me", headers=author["headers"])).status_code == 200
    assert (await client.get("/me", headers={"Authorization": f"Bearer {author['tokens']['refresh_token']}"})).status_code == 401
    assert (await client.post("/refresh", json={"refresh_token": author["tokens"]["access_token"]})).status_code == 401
    assert (await client.post("/refresh", json={"refresh_token": author["tokens"]["refresh_token"]})).status_code == 200
    assert (await client.get("/admin/panel", headers=author["headers"])).status_code == 403


@pytest.mark.parametrize("user_id", ["bad-id", [], {}, None, True, 1.5, 10**30])
async def test_invalid_token_subject_is_401(client, user_id):
    access = create_access_token({"user_id": user_id})
    refresh = create_refresh_token({"user_id": user_id})
    assert (await client.get("/me", headers={"Authorization": f"Bearer {access}"})).status_code == 401
    assert (await client.post("/refresh", json={"refresh_token": refresh})).status_code == 401


async def test_public_posts_and_draft_privacy(client, accounts):
    author, reader = accounts
    draft = await create_post(client, author)
    published = await create_post(client, author, is_published=True)
    public = await client.get(f"/authors/{author['id']}/posts")
    assert public.status_code == 200
    assert [p["id"] for p in public.json()["items"]] == [published["id"]]
    assert (await client.get(f"/posts/{published['id']}")).status_code == 200
    assert (await client.get(f"/posts/{draft['id']}")).status_code == 404
    assert (await client.get(f"/posts/{draft['id']}", headers=reader["headers"])).status_code == 404
    assert (await client.get(f"/posts/{draft['id']}", headers=author["headers"])).status_code == 200
    assert (await client.put(f"/posts/{draft['id']}", headers=reader["headers"], json={"title": "stolen"})).status_code == 404
    assert (await client.delete(f"/posts/{draft['id']}", headers=reader["headers"])).status_code == 404
    assert (await client.get(f"/posts/{published['id']}", headers={"Authorization": "Bearer invalid"})).status_code == 401
    assert (await client.get("/feed")).status_code == 401


async def test_only_publication_transition_records_deliveries(client, accounts, db):
    author, reader = accounts
    await enable_publication_emails(client, db, reader)
    await client.post("/subscriptions", headers=reader["headers"], json={"author_id": author["id"]})
    draft = await create_post(client, author)
    url = f"/posts/{draft['id']}"
    for fields, count in [({"title": "Draft edit"}, 0), ({"is_published": True}, 1),
                          ({"title": "Typo fix"}, 1), ({"is_published": True}, 1),
                          ({"is_published": False}, 1), ({"is_published": True}, 2)]:
        result = await client.put(url, headers=author["headers"], json=fields)
        assert result.status_code == 200, result.text
        deliveries = (await db.scalars(select(EmailDelivery).where(EmailDelivery.post_id == draft["id"]))).all()
        assert len(deliveries) == count
        assert all(row.recipient_id == reader["id"] for row in deliveries)
        assert len({row.publication_id for row in deliveries}) == count


async def test_publication_survives_unavailable_broker(client, accounts, db, monkeypatch):
    author, reader = accounts
    await enable_publication_emails(client, db, reader)
    await client.post("/subscriptions", headers=reader["headers"], json={"author_id": author["id"]})
    send = Mock(side_effect=ConnectionError("Broker unavailable"))
    monkeypatch.setattr(celery_app, "send_task", send)
    post = await create_post(client, author, is_published=True)
    deliveries = (await db.scalars(select(EmailDelivery).where(EmailDelivery.post_id == post["id"]))).all()
    assert len(deliveries) == 1
    assert deliveries[0].status == "pending"
    send.assert_not_called()


async def test_publication_and_deliveries_roll_back_together(client, accounts, db, monkeypatch):
    author, reader = accounts
    await enable_publication_emails(client, db, reader)
    await client.post("/subscriptions", headers=reader["headers"], json={"author_id": author["id"]})
    original = crud_posts.record_publication_emails
    post_ids = []

    async def fail_after_recording(session, post):
        post_ids.append(post.id)
        await original(session, post)
        await session.flush()
        raise RuntimeError("Publication transaction interrupted")

    monkeypatch.setattr(crud_posts, "record_publication_emails", fail_after_recording)
    with pytest.raises(RuntimeError, match="transaction interrupted"):
        async with db.begin_nested():
            await crud_posts.create_post(db, PostCreate(title="Rollback", content="Body", is_published=True), author["id"])
    assert await db.get(Post, post_ids[0]) is None
    assert (await db.scalars(select(EmailDelivery).where(EmailDelivery.post_id == post_ids[0]))).all() == []


async def test_public_authors_do_not_expose_email(client, accounts):
    author, reader = accounts
    await client.post("/subscriptions", headers=reader["headers"], json={"author_id": author["id"]})
    subscriptions = (await client.get("/subscriptions", headers=reader["headers"])).json()["items"]
    subscribers = (await client.get("/subscribers", headers=author["headers"])).json()["items"]
    assert subscriptions[0]["id"] == author["id"]
    assert subscribers[0]["id"] == reader["id"]
    assert all("email" not in user for user in subscriptions + subscribers)
    post = await create_post(client, author, is_published=True)
    feed = (await client.get("/feed", headers=reader["headers"])).json()["items"]
    assert feed[0]["id"] == post["id"]
    assert "email" not in feed[0]
    assert author["email"] not in str(feed)
    assert (await client.get("/me", headers=reader["headers"])).json()["email"] == reader["email"]


async def test_feed_pagination_reflects_changes(client, accounts):
    author, reader = accounts
    headers = reader["headers"]
    first = await create_post(client, author, is_published=True)
    second = await create_post(client, author, title="Second", is_published=True)
    await create_post(client, author, title="Hidden draft")
    assert (await client.get("/feed", headers=headers)).json()["items"] == []
    assert (await client.post("/subscriptions", headers=headers, json={"author_id": author["id"]})).status_code == 201
    page1 = (await client.get("/feed?limit=1", headers=headers)).json()
    page2 = (await client.get("/feed", params={"limit": 1, "cursor": page1["next_cursor"]}, headers=headers)).json()
    assert [p["id"] for p in page1["items"]] == [second["id"]]
    assert [p["id"] for p in page2["items"]] == [first["id"]]
    assert page1["has_more"] is True
    assert page2["has_more"] is False and page2["next_cursor"] is None
    await client.put(f"/posts/{second['id']}", headers=author["headers"], json={"title": "Edited"})
    assert (await client.get("/feed?limit=1", headers=headers)).json()["items"][0]["title"] == "Edited"
    await client.put(f"/posts/{second['id']}", headers=author["headers"], json={"is_published": False})
    assert [p["id"] for p in (await client.get("/feed", headers=headers)).json()["items"]] == [first["id"]]
    await client.delete(f"/posts/{first['id']}", headers=author["headers"])
    assert (await client.get("/feed", headers=headers)).json()["items"] == []
    await create_post(client, author, is_published=True)
    assert len((await client.get("/feed", headers=headers)).json()["items"]) == 1
    assert (await client.delete(f"/subscriptions/{author['id']}", headers=headers)).status_code == 204
    assert (await client.get("/feed", headers=headers)).json()["items"] == []
    assert (await client.delete(f"/subscriptions/{author['id']}", headers=headers)).status_code == 404


async def test_subscriptions_unique_in_database(client, accounts, db):
    author, reader = accounts
    payload = {"author_id": author["id"]}
    assert (await client.post("/subscriptions", headers=author["headers"], json=payload)).status_code == 400
    assert (await client.post("/subscriptions", headers=reader["headers"], json=payload)).status_code == 201
    assert (await client.post("/subscriptions", headers=reader["headers"], json=payload)).status_code == 400
    with pytest.raises(IntegrityError):
        async with db.begin_nested():
            db.add(Subscription(subscriber_id=reader["id"], author_id=author["id"]))
            await db.flush()
    assert len((await db.execute(select(Subscription).where(Subscription.subscriber_id == reader["id"]))).scalars().all()) == 1


async def test_delete_author_removes_feed_posts(client, accounts):
    author, reader = accounts
    await client.post("/subscriptions", headers=reader["headers"], json={"author_id": author["id"]})
    await create_post(client, author, is_published=True)
    assert len((await client.get("/feed", headers=reader["headers"])).json()["items"]) == 1
    response = await client.delete(f"/users/{author['id']}", headers=author["headers"])
    assert response.status_code == 204, response.text
    assert (await client.get("/feed", headers=reader["headers"])).json()["items"] == []


@pytest.mark.parametrize("field", ["title", "content", "is_published"])
async def test_update_null_rejected(client, accounts, field):
    author, _ = accounts
    post = await create_post(client, author)
    assert (await client.put(f"/posts/{post['id']}", headers=author["headers"], json={field: None})).status_code == 422


async def test_migration_indexes(db):
    connection = await db.connection()
    indexes = await connection.run_sync(lambda conn: inspect(conn).get_indexes("posts"))
    assert any(i["column_names"] == ["author_id", "is_published", "created_at", "id"] for i in indexes)
    assert any(i["column_names"] == ["author_id", "created_at", "id"] for i in indexes)
    feed_index = next(i for i in indexes if i["name"] == "ix_posts_published_created_id")
    assert feed_index["column_names"] == ["created_at", "id"]
    assert "is_published IS TRUE" in feed_index["dialect_options"]["postgresql_where"]
    indexes = await connection.run_sync(lambda conn: inspect(conn).get_indexes("subscriptions"))
    assert any(i["column_names"] == ["author_id", "created_at", "id"] for i in indexes)
    assert any(i["column_names"] == ["subscriber_id", "created_at", "id"] for i in indexes)
