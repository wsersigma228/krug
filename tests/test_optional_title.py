from unittest.mock import Mock

import pytest

from backend.models import User
from backend.tasks import email_tasks


async def test_optional_titles_persist_and_remain_searchable(client, accounts):
    author, reader = accounts
    headers = author["headers"]
    subscribed = await client.post("/subscriptions", headers=reader["headers"], json={"author_id": author["id"]})
    assert subscribed.status_code == 201, subscribed.text
    posts = []
    for title_fields in ({}, {"title": ""}, {"title": " \t\n "}):
        response = await client.post("/posts", headers=headers, json={
            "content": "uniquetitlelesssearch body", "is_published": True, **title_fields,
        })
        assert response.status_code == 201, response.text
        post = response.json()
        assert post["title"] == ""
        assert (await client.get(f"/posts/{post['id']}")).json()["title"] == ""
        posts.append(post)
    ids = {post["id"] for post in posts}
    feed = await client.get("/feed", headers=reader["headers"])
    assert feed.status_code == 200, feed.text
    assert {post["id"] for post in feed.json()["items"]} == ids
    for route in ("/explore", "/posts"):
        response = await client.get(route, headers=headers, params={"search": "uniquetitlelesssearch"})
        assert response.status_code == 200, response.text
        assert {post["id"] for post in response.json()["items"]} == ids
        assert all(post["title"] == "" for post in response.json()["items"])

    response = await client.post("/posts", headers=headers, json={"title": "  Existing title  ", "content": "Original body"})
    assert response.status_code == 201, response.text
    post = response.json()
    assert post["title"] == "Existing title"
    route = f"/posts/{post['id']}"
    kept = await client.put(route, headers=headers, json={"content": "Edited body"})
    assert kept.status_code == 200, kept.text
    assert kept.json()["title"] == "Existing title"
    for title in (None, "x" * 201):
        assert (await client.post("/posts", headers=headers, json={"title": title, "content": "Body"})).status_code == 422
        assert (await client.put(route, headers=headers, json={"title": title})).status_code == 422
    for title in ("", " \t\n "):
        cleared = await client.put(route, headers=headers, json={"title": title})
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["title"] == ""
        assert (await client.get(route, headers=headers)).json()["title"] == ""
    for fields in ({}, {"content": ""}, {"content": None}):
        assert (await client.post("/posts", headers=headers, json=fields)).status_code == 422


@pytest.mark.parametrize("language", ["ru", "en"])
async def test_titleless_publication_mail_uses_content_preview(client, accounts, db, monkeypatch, language):
    author, reader = accounts
    user = await db.get(User, reader["id"])
    user.email_verified = user.email_publications = True
    user.language = language
    await db.commit()
    await client.post("/subscriptions", headers=reader["headers"], json={"author_id": author["id"]})
    content = "  First\n\twords   " + "long preview " * 12
    preview = " ".join(content.split())[:80]
    response = await client.post("/posts", headers=author["headers"], json={"content": content, "is_published": True})
    assert response.status_code == 201, response.text
    send = Mock(return_value=True)
    monkeypatch.setattr(email_tasks, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(email_tasks, "_send_email_sync", send)
    assert await email_tasks._deliver_pending(db) == 1
    send.assert_called_once()
    subject, body, recipient = send.call_args.args
    prefix = "Новая публикация от" if language == "ru" else "New post from"
    assert subject == f"{prefix} {author['username']}: {preview}"
    assert f'"{preview}"' in body
    assert ("Здравствуйте!" if language == "ru" else "Hello!") in body
    assert recipient == reader["email"]
