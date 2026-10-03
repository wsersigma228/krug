from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from backend.models import Post
from tests.test_pagination import get_page


async def add_post(db, author, title="Notes", content="Body", **fields):
    post = Post(author_id=author["id"], title=title, content=content, **fields)
    db.add(post)
    await db.commit()
    return post


@pytest.mark.parametrize("language,title,content,query", [
    ("simple", "Salom", "Dunyo haqida", "dunyo"),
    ("simple", "Notizen", "Über Datenbanken", "über"),
    ("simple", "Mixed", "Python и PostgreSQL", "python PostgreSQL"),
    ("russian", "Заметки", "Кошки играют", "кошка"),
    ("english", "Notes", "The runners are running", "run"),
])
async def test_languages_and_content(client, accounts, db, language, title, content, query):
    author, _ = accounts
    post = await add_post(db, author, title, content)
    page = await get_page(client, "/posts", author["headers"], search=query, search_language=language)
    assert [item["id"] for item in page["items"]] == [post.id]


async def test_ranked_pages_and_permissions(client, accounts, db):
    author, other = accounts
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    body = await add_post(db, author, content="python", created_at=now + timedelta(days=1), is_published=True)
    title = await add_post(db, author, title="python", created_at=now, is_published=True)
    tie = await add_post(db, author, title="python", created_at=now, is_published=True)
    await add_post(db, author, title="python", is_published=False)
    await add_post(db, other, title="python", is_published=True)
    params = dict(search="python", is_published="true", limit=1)
    first = await get_page(client, "/posts", author["headers"], **params)
    assert first["items"][0]["id"] == tie.id
    for changes in ({"search_language": "english"}, {"search": "other"}, {"is_published": "false"}):
        response = await client.get("/posts", headers=author["headers"], params={
            **params, **changes, "cursor": first["next_cursor"],
        })
        assert response.status_code == 422
    response = await client.get("/posts", headers=other["headers"], params={**params, "cursor": first["next_cursor"]})
    assert response.status_code == 422
    await db.delete(tie)
    await db.commit()
    second = await get_page(client, "/posts", author["headers"], **params, cursor=first["next_cursor"])
    third = await get_page(client, "/posts", author["headers"], **params, cursor=second["next_cursor"])
    assert [second["items"][0]["id"], third["items"][0]["id"]] == [title.id, body.id]
    assert not third["has_more"]


async def test_vector_refresh_and_sql_updates(client, accounts, db):
    author, _ = accounts
    post = await add_post(db, author, content="oldtoken")
    response = await client.put(f"/posts/{post.id}", headers=author["headers"], json={"content": "newtoken"})
    assert response.status_code == 200
    assert not (await get_page(client, "/posts", author["headers"], search="oldtoken"))["items"]
    assert (await get_page(client, "/posts", author["headers"], search="newtoken"))["items"]
    await db.execute(text("UPDATE posts SET title = 'directtoken' WHERE id = :id"), {"id": post.id})
    assert (await get_page(client, "/posts", author["headers"], search="directtoken"))["items"]


@pytest.mark.parametrize("query,language", [("!!!", "simple"), ("the and", "english"), ("несуществующее", "russian")])
async def test_empty_matches(client, accounts, db, query, language):
    author, _ = accounts
    await add_post(db, author)
    assert await get_page(client, "/posts", author["headers"], search=query, search_language=language) == {
        "items": [], "next_cursor": None, "has_more": False,
    }


async def test_whitespace_and_invalid_language(client, accounts, db):
    author, _ = accounts
    post = await add_post(db, author)
    assert (await get_page(client, "/posts", author["headers"], search="   "))["items"][0]["id"] == post.id
    response = await client.get("/posts", headers=author["headers"], params={"search": "x", "search_language": "unknown"})
    assert response.status_code == 422


async def test_web_query_syntax(client, accounts, db):
    author, _ = accounts
    first = await add_post(db, author, content="red green blue")
    await add_post(db, author, content="red blue green")
    page = await get_page(client, "/posts", author["headers"], search='"red green" -yellow')
    assert [p["id"] for p in page["items"]] == [first.id]
    page = await get_page(client, "/posts", author["headers"], search="missing OR green")
    assert len(page["items"]) == 2
