from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from backend.crud.subscriptions import get_subscribers
from backend.models import Post, Subscription, User
from backend.pagination import cursor_scope, encode_cursor


async def seed_posts(db, author_id, count, **fields):
    # Equal timestamps exercise the ID tie-breaker on every page.
    rows = [Post(author_id=author_id, title=f"Post {i}", content="Body", is_published=True,
                 created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), **fields) for i in range(count)]
    db.add_all(rows)
    await db.commit()
    return rows


async def get_page(client, url, headers, **params):
    response = await client.get(url, headers=headers, params=params)
    assert response.status_code == 200, response.text
    page = response.json()
    assert set(page) == {"items", "next_cursor", "has_more"}
    assert page["has_more"] == (page["next_cursor"] is not None)
    return page


@pytest.mark.parametrize("endpoint", ["posts", "feed", "author"])
@pytest.mark.parametrize("count", [0, 1, 2, 3, 4, 5])
async def test_walk_post_pages(client, accounts, db, endpoint, count):
    author, reader = accounts
    rows = await seed_posts(db, author["id"], count)
    db.add(Post(author_id=author["id"], title="Draft", content="Private", is_published=False))
    await seed_posts(db, reader["id"], 1)
    db.add(Subscription(subscriber_id=reader["id"], author_id=author["id"]))
    await db.commit()
    url, headers, filters = {
        "posts": ("/posts", author["headers"], {"is_published": "true"}),
        "feed": ("/feed", reader["headers"], {}),
        "author": (f"/authors/{author['id']}/posts", {}, {}),
    }[endpoint]
    seen = []
    params = {"limit": 2, **filters}
    for _ in range(count + 1):
        page = await get_page(client, url, headers, **params)
        assert len(page["items"]) <= 2
        seen.extend(item["id"] for item in page["items"])
        if not page["has_more"]:
            break
        params["cursor"] = page["next_cursor"]
    else:
        pytest.fail("Pagination never reached the end")
    assert seen == [row.id for row in reversed(rows)]


@pytest.mark.parametrize("endpoint", ["posts", "feed", "author"])
async def test_new_posts_and_deleted_boundary_do_not_shift_pages(client, accounts, db, endpoint):
    author, reader = accounts
    rows = await seed_posts(db, author["id"], 5)
    db.add(Subscription(subscriber_id=reader["id"], author_id=author["id"]))
    await db.commit()
    url, headers = {
        "posts": ("/posts", author["headers"]),
        "feed": ("/feed", reader["headers"]),
        "author": (f"/authors/{author['id']}/posts", {}),
    }[endpoint]
    first = await get_page(client, url, headers, limit=2)
    assert [item["id"] for item in first["items"]] == [rows[4].id, rows[3].id]
    await client.post("/posts", headers=author["headers"], json={"title": "New", "content": "Body", "is_published": True})
    response = await client.delete(f"/posts/{rows[3].id}", headers=author["headers"])
    assert response.status_code == 204
    second = await get_page(client, url, headers, limit=3, cursor=first["next_cursor"])
    assert [item["id"] for item in second["items"]] == [row.id for row in reversed(rows[:3])]
    assert second["has_more"] is False


async def test_timestamp_takes_priority_over_id(client, accounts, db):
    author, _ = accounts
    rows = await seed_posts(db, author["id"], 3)
    rows[0].created_at += timedelta(days=1)
    rows[2].created_at -= timedelta(days=1)
    await db.commit()
    page = await get_page(client, "/posts", author["headers"], limit=1)
    seen = [page["items"][0]["id"]]
    while page["has_more"]:
        page = await get_page(client, "/posts", author["headers"], limit=1, cursor=page["next_cursor"])
        seen.append(page["items"][0]["id"])
    assert seen == [row.id for row in rows]


async def test_filters_are_preserved_and_cursor_is_scoped(client, accounts, db):
    author, reader = accounts
    rows = await seed_posts(db, author["id"], 4)
    rows[0].title = rows[2].title = "Python"
    rows[1].is_published = False
    await db.commit()
    filters = {"is_published": "true", "search": "Python"}
    first = await get_page(client, "/posts", author["headers"], limit=1, **filters)
    cursor = first["next_cursor"]
    second = await get_page(client, "/posts", author["headers"], limit=1, cursor=cursor, **filters)
    assert [p["id"] for p in first["items"] + second["items"]] == [rows[2].id, rows[0].id]
    for url, headers, params in [
        ("/posts", author["headers"], {}),
        ("/posts", author["headers"], {**filters, "search": "Other"}),
        ("/posts", author["headers"], {**filters, "is_published": "false"}),
        ("/posts", reader["headers"], filters),
        ("/feed", author["headers"], {}),
        (f"/authors/{author['id']}/posts", {}, {}),
    ]:
        response = await client.get(url, headers=headers, params={"cursor": cursor, **params})
        assert response.status_code == 422, response.text


@pytest.mark.parametrize("endpoint", ["posts", "feed", "author", "subscriptions", "subscribers"])
@pytest.mark.parametrize("params", [
    {"offset": 0}, {"offset": 10}, {"limit": 0}, {"limit": 101}, {"limit": "oops"},
    {"cursor": ""}, {"cursor": "not-a-cursor"}, {"cursor": "a" * 2049},
])
async def test_invalid_page_parameters(client, accounts, endpoint, params):
    author, _ = accounts
    url = f"/authors/{author['id']}/posts" if endpoint == "author" else f"/{endpoint}"
    response = await client.get(url, headers=author["headers"], params=params)
    assert response.status_code == 422, response.text


async def test_tampered_feed_cursor_is_rejected(client, accounts, db):
    author, reader = accounts
    await seed_posts(db, author["id"], 2)
    db.add(Subscription(subscriber_id=reader["id"], author_id=author["id"]))
    await db.commit()
    page = await get_page(client, "/feed", reader["headers"], limit=1)
    data, signature = page["next_cursor"].split(".")
    cursor = data + "." + ("A" if signature[0] != "A" else "B") + signature[1:]
    response = await client.get("/feed", headers=reader["headers"], params={"limit": 1, "cursor": cursor})
    assert response.status_code == 422


async def test_feed_pages_reflect_unpublished_posts(client, accounts, db):
    author, reader = accounts
    rows = await seed_posts(db, author["id"], 3)
    db.add(Subscription(subscriber_id=reader["id"], author_id=author["id"]))
    await db.commit()
    first = await get_page(client, "/feed", reader["headers"], limit=1)
    cursor = first["next_cursor"]
    second = await get_page(client, "/feed", reader["headers"], limit=1, cursor=cursor)
    assert first["items"][0]["id"] == rows[2].id
    assert second["items"][0]["id"] == rows[1].id
    response = await client.put(f"/posts/{rows[1].id}", headers=author["headers"], json={"is_published": False})
    assert response.status_code == 200
    refreshed = await get_page(client, "/feed", reader["headers"], limit=1, cursor=cursor)
    assert [item["id"] for item in refreshed["items"]] == [rows[0].id]
    assert refreshed["has_more"] is False


@pytest.mark.parametrize("followers", [False, True])
async def test_subscription_pages_use_follow_time_and_survive_unsubscribe(client, accounts, db, followers):
    author, reader = accounts
    others = [User(username=f"page_{uuid4().hex}", hashed_password="unused") for _ in range(5)]
    db.add_all(others)
    await db.flush()
    # Follow users in reverse account order to distinguish the two sorts.
    others.reverse()
    subscriptions = [Subscription(
        author_id=author["id"] if followers else user.id,
        subscriber_id=user.id if followers else author["id"],
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    ) for user in others]
    db.add_all(subscriptions)
    await db.commit()
    url = "/subscribers" if followers else "/subscriptions"
    first = await get_page(client, url, author["headers"], limit=2)
    assert [item["id"] for item in first["items"]] == [user.id for user in reversed(others[-2:])]
    await db.delete(subscriptions[-2])
    db.add(Subscription(author_id=author["id"] if followers else reader["id"],
                        subscriber_id=reader["id"] if followers else author["id"]))
    await db.commit()
    second = await get_page(client, url, author["headers"], limit=3, cursor=first["next_cursor"])
    assert [item["id"] for item in second["items"]] == [user.id for user in reversed(others[:3])]
    assert second["has_more"] is False
    response = await client.get(url, headers=reader["headers"], params={"cursor": first["next_cursor"]})
    assert response.status_code == 422


async def test_internal_subscriber_lookup_is_not_paginated(client, accounts, db):
    author, _ = accounts
    users = [User(username=f"mail_{uuid4().hex}", hashed_password="unused") for _ in range(101)]
    db.add_all(users)
    await db.flush()
    db.add_all([Subscription(subscriber_id=user.id, author_id=author["id"]) for user in users])
    await db.commit()
    page = await get_page(client, "/subscribers", author["headers"])
    assert len(page["items"]) == 100 and page["has_more"] is True
    assert len(await get_subscribers(db, author["id"])) == 101


async def test_timezone_cursor_and_deleted_last_page(client, accounts, db):
    author, _ = accounts
    rows = await seed_posts(db, author["id"], 2)
    scope = cursor_scope("posts", user_id=author["id"], is_published=None, search=None)
    timestamp = rows[1].created_at.astimezone(timezone(timedelta(hours=5)))
    cursor = encode_cursor(timestamp, rows[1].id, scope)
    page = await get_page(client, "/posts", author["headers"], cursor=cursor)
    assert [item["id"] for item in page["items"]] == [rows[0].id]
    await db.delete(rows[0])
    await db.commit()
    page = await get_page(client, "/posts", author["headers"], cursor=cursor)
    assert page == {"items": [], "has_more": False, "next_cursor": None}


async def test_author_cursor_cannot_be_reused_for_another_author(client, accounts, db):
    author, reader = accounts
    await seed_posts(db, author["id"], 2)
    page = await get_page(client, f"/authors/{author['id']}/posts", {}, limit=1)
    response = await client.get(f"/authors/{reader['id']}/posts", params={"cursor": page["next_cursor"]})
    assert response.status_code == 422


@pytest.mark.parametrize("endpoint", ["subscriptions", "subscribers"])
async def test_empty_subscription_pages(client, accounts, endpoint):
    author, _ = accounts
    page = await get_page(client, f"/{endpoint}", author["headers"])
    assert page == {"items": [], "next_cursor": None, "has_more": False}
