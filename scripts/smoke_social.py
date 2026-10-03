"""Real HTTP photo persistence check: prepare, recreate web, then check.

The temporary state contains test-only credentials; it is removed by check.
"""
import argparse
from io import BytesIO
import json
import os
from pathlib import Path
import secrets

import httpx
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "check"])
    parser.add_argument("state", type=Path)
    args = parser.parse_args()
    with httpx.Client(base_url=os.getenv("APP_URL", "http://127.0.0.1:8000"), timeout=20) as client:
        if args.action == "prepare":
            fd = os.open(args.state, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            users = []
            try:
                for role in ("author", "reader"):
                    username = f"photo_{role}_{secrets.token_hex(5)}"
                    password = secrets.token_urlsafe(20)
                    response = client.post("/users", json={"username": username, "password": password})
                    response.raise_for_status()
                    user = response.json()
                    response = client.post("/login", json={"username": username, "password": password})
                    response.raise_for_status()
                    user["headers"] = {"Authorization": "Bearer " + response.json()["access_token"]}
                    users.append(user)
                author, reader = users
                response = client.post("/posts", headers=author["headers"], json={
                    "title": "Persistence check", "content": "temporary", "is_published": True})
                response.raise_for_status()
                post_id = response.json()["id"]
                image = BytesIO()
                Image.new("RGB", (40, 30), "green").save(image, format="PNG")
                response = client.put(f"/posts/{post_id}/image", headers=author["headers"], content=image.getvalue())
                response.raise_for_status()
                assert response.json()["image_url"]
                for _ in range(2):
                    assert client.put(f"/posts/{post_id}/likes", headers=reader["headers"]).status_code == 200
                response = client.post(f"/posts/{post_id}/comments", headers=reader["headers"], json={"content": "Survives recreation"})
                response.raise_for_status()
                with os.fdopen(fd, "w") as file:
                    json.dump({"users": users, "post_id": post_id}, file)
                print("Temporary published photo, unique like and comment prepared")
            except Exception:
                for user in reversed(users):
                    client.delete(f"/users/{user['id']}", headers=user["headers"])
                args.state.unlink(missing_ok=True)
                raise
        else:
            state = json.loads(args.state.read_text())
            author, reader = state["users"]
            post_id = state["post_id"]
            try:
                response = client.get(f"/posts/{post_id}/image")
                assert response.status_code == 200, response.text
                with Image.open(BytesIO(response.content)) as image:
                    assert image.size == (40, 30) and image.format == "JPEG"
                assert client.get(f"/posts/{post_id}/likes", headers=reader["headers"]).json() == {"count": 1, "liked": True}
                comments = client.get(f"/posts/{post_id}/comments").json()["items"]
                assert len(comments) == 1 and comments[0]["content"] == "Survives recreation"
                assert client.get(f"/authors/{author['id']}").json()["posts_count"] == 1
                response = client.put(f"/posts/{post_id}", headers=author["headers"], json={"is_published": False})
                assert response.status_code == 200
                for suffix in ("image", "likes", "comments"):
                    assert client.get(f"/posts/{post_id}/{suffix}").status_code == 404
                print("Photo, like and comment survived recreation; hidden content is inaccessible: OK")
            finally:
                for user in reversed(state["users"]):
                    response = client.delete(f"/users/{user['id']}", headers=user["headers"])
                    assert response.status_code == 204, response.text
                args.state.unlink()
                print("Temporary accounts, photos and state removed")


if __name__ == "__main__":
    main()
