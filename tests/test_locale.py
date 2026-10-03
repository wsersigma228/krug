from unittest.mock import Mock
from types import SimpleNamespace
from uuid import uuid4

import pytest

from backend.models import User
from backend.tasks import email_tasks


async def test_language_is_nullable_private_and_persists(client, accounts):
    author, reader = accounts
    assert author["language"] is None
    for language in ("ru", "en"):
        changed = await client.patch("/me/language", headers=author["headers"], json={"language": language})
        assert changed.status_code == 200, changed.text
        assert changed.json() == {"language": language}
        assert (await client.get("/me", headers=author["headers"])).json()["language"] == language
    assert (await client.get("/me", headers=reader["headers"])).json()["language"] is None
    assert "language" not in (await client.get(f"/authors/{author['id']}")).json()
    tokens = (await client.post("/login", json={"username": author["username"], "password": "test-password"})).json()
    assert (await client.get("/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})).json()["language"] == "en"
    await client.post("/logout", headers=author["headers"])
    assert (await client.patch("/me/language", headers=author["headers"], json={"language": "ru"})).status_code == 401


@pytest.mark.parametrize("language", ["ru", "en"])
async def test_registration_accepts_language(client, language):
    response = await client.post("/users", json={
        "username": f"locale_{uuid4().hex[:10]}", "password": "test-password", "language": language,
    })
    assert response.status_code == 201, response.text
    assert response.json()["language"] == language


@pytest.mark.parametrize("payload", [{}, {"language": None}, {"language": "fr"}, {"language": "RU"},
                                     {"language": 1}, {"language": "en", "bio": "unexpected"}])
async def test_language_rejects_invalid_changes(client, accounts, payload):
    account, _ = accounts
    assert (await client.patch("/me/language", headers=account["headers"], json=payload)).status_code == 422
    assert (await client.get("/me", headers=account["headers"])).json()["language"] is None


async def test_language_requires_authentication(client):
    assert (await client.patch("/me/language", json={"language": "ru"})).status_code in (401, 403)


async def test_initial_language_does_not_overwrite_a_saved_choice(client, accounts):
    account, _ = accounts
    headers = account["headers"]
    first = await client.patch("/me/language?initialize=true", headers=headers, json={"language": "ru"})
    assert first.json() == {"language": "ru"}
    later = await client.patch("/me/language?initialize=true", headers=headers, json={"language": "en"})
    assert later.json() == {"language": "ru"}
    changed = await client.patch("/me/language", headers=headers, json={"language": "en"})
    assert changed.json() == {"language": "en"}


async def test_language_rechecks_revocation_after_authentication(accounts, db):
    from fastapi import HTTPException
    from backend.routes.users import change_language
    from backend.schemas import LanguageSettings

    account, _ = accounts
    user = await db.get(User, account["id"])
    authenticated = SimpleNamespace(id=user.id, token_version=user.token_version)
    user.token_version += 1
    await db.commit()
    with pytest.raises(HTTPException) as error:
        await change_language(LanguageSettings(language="ru"), db, authenticated)
    assert error.value.status_code == 401
    assert user.language is None


@pytest.mark.parametrize("language", ["ru", "en", None])
@pytest.mark.parametrize("kind", ["verify", "reset", "publication"])
async def test_mail_uses_current_recipient_language(client, accounts, db, monkeypatch, language, kind):
    author, reader = accounts
    if kind == "verify":
        response = await client.post("/auth/email-verification/request", headers=reader["headers"])
    elif kind == "reset":
        response = await client.post("/auth/password-reset/request", json={"email": reader["email"]})
    else:
        user = await db.get(User, reader["id"])
        user.email_verified = user.email_publications = True
        await db.commit()
        await client.post("/subscriptions", headers=reader["headers"], json={"author_id": author["id"]})
        response = await client.post("/posts", headers=author["headers"], json={
            "title": "Оригинальный title", "content": "Untranslated content", "is_published": True,
        })
    assert response.status_code in (201, 202), response.text
    # Change after enqueueing: delivery must read the recipient's current preference.
    user = await db.get(User, reader["id"])
    user.language = language
    writer = await db.get(User, author["id"])
    writer.language = "en" if language == "ru" else "ru"
    await db.commit()
    send = Mock(return_value=True)
    monkeypatch.setattr(email_tasks, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(email_tasks, "_send_email_sync", send)
    assert await email_tasks._deliver_pending(db) == 1
    send.assert_called_once()
    subject, body, recipient = send.call_args.args
    assert recipient == reader["email"]
    if kind == "publication":
        prefix = "Новая публикация от" if language == "ru" else "New post from"
        assert subject == f"{prefix} {author['username']}: Оригинальный title"
        assert '"Оригинальный title"' in body
        assert ("Здравствуйте!" if language == "ru" else "Hello!") in body
    else:
        expected = {
            "ru": {"verify": "Подтвердите email", "reset": "Сброс пароля"},
            "en": {"verify": "Verify your email", "reset": "Reset your password"},
        }
        assert subject == expected[language or "en"][kind]
        assert ("Срок действия ссылки" if language == "ru" else "This link expires") in body
        path = "verify-email" if kind == "verify" else "reset-password"
        language_query = f"?lang={language}" if language else ""
        assert f"/{path}{language_query}#token=" in body
