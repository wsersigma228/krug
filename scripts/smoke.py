"""Exercise the running stack with temporary accounts that have no email addresses.

Run from the project root: .venv/bin/python -m scripts.smoke
"""
import secrets
import os

import httpx
from backend.tasks.celery_app import celery_app


def main():
    users = []
    client = httpx.Client(base_url=os.getenv("APP_URL", "http://127.0.0.1:8000"), timeout=15)
    try:
        assert client.get("/").json() == {"ok": True}
        assert client.get("/docs").status_code == 200
        for role in ("author", "reader"):
            username = f"smoke_{role}_{secrets.token_hex(5)}"
            password = secrets.token_urlsafe(24)
            response = client.post("/users", json={"username": username, "password": password})
            response.raise_for_status()
            user = response.json()
            tokens = client.post("/login", json={"username": username, "password": password})
            tokens.raise_for_status()
            user["headers"] = {"Authorization": "Bearer " + tokens.json()["access_token"]}
            users.append(user)
        author, reader = users
        response = client.post("/subscriptions", headers=reader["headers"], json={"author_id": author["id"]})
        assert response.status_code == 201, response.text
        response = client.post("/posts", headers=author["headers"], json={
            "title": "Smoke test", "content": "temporary", "is_published": True,
        })
        assert response.status_code == 201, response.text
        post_id = response.json()["id"]
        assert client.get(f"/posts/{post_id}").status_code == 200
        feed = client.get("/feed?limit=1", headers=reader["headers"])
        assert feed.json()["items"][0]["id"] == post_id
        response = client.put(f"/posts/{post_id}", headers=author["headers"], json={"title": "Updated"})
        assert response.status_code == 200, response.text
        assert client.get("/feed?limit=1", headers=reader["headers"]).json()["items"][0]["title"] == "Updated"
        response = client.post("/posts", headers=author["headers"], json={
            "title": "Another", "content": "temporary", "is_published": True,
        })
        assert response.status_code == 201, response.text
        first = client.get("/feed?limit=1", headers=reader["headers"]).json()
        assert first["has_more"] is True
        second = client.get("/feed", headers=reader["headers"], params={"limit": 1, "cursor": first["next_cursor"]}).json()
        assert second["items"][0]["id"] == post_id
        assert second["has_more"] is False and second["next_cursor"] is None
        # Ping the worker without dispatching real users' pending emails.
        assert celery_app.control.ping(timeout=5), "No Celery worker replied"
        response = client.delete(f"/subscriptions/{author['id']}", headers=reader["headers"])
        assert response.status_code == 204
        assert client.get("/feed", headers=reader["headers"]).json()["items"] == []
        print("HTTP, auth, public posts, current feed, unsubscribe and Celery worker: OK")
    finally:
        for user in reversed(users):
            response = client.delete(f"/users/{user['id']}", headers=user["headers"])
            assert response.status_code == 204, response.text
        client.close()
        print("Temporary smoke-test accounts removed")


if __name__ == "__main__":
    main()
