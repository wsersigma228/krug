"""Real HTTP + worker + Mailpit check; run only with the development mail overlay."""
import re
import secrets
import time
import os

import httpx


def main():
    username = f"account_smoke_{secrets.token_hex(6)}"
    email = f"{username}@example.test"
    password = secrets.token_urlsafe(24)
    user_id = None
    author_id = None
    author_name = f"{username}_author"
    author_password = secrets.token_urlsafe(24)
    message_ids = []
    with httpx.Client(base_url=os.getenv("APP_URL", "http://127.0.0.1:8000"), timeout=15) as app, httpx.Client(
        base_url=os.getenv("MAILPIT_URL", "http://127.0.0.1:8025"), timeout=15,
    ) as mailbox:
        mailbox.get("/api/v1/info").raise_for_status()

        def login():
            response = app.post("/login", json={"username": username, "password": password})
            response.raise_for_status()
            return response.json()

        def read_link(subject, token_required=True):
            deadline = time.monotonic() + 75
            while time.monotonic() < deadline:
                response = mailbox.get("/api/v1/messages", params={"limit": 100})
                response.raise_for_status()
                for message in response.json()["messages"]:
                    if message["Subject"] == subject and any(to["Address"] == email for to in message["To"]):
                        message_ids.append(message["ID"])
                        content = mailbox.get(f"/api/v1/message/{message['ID']}")
                        content.raise_for_status()
                        if not token_required:
                            return content.json()["Text"]
                        match = re.search(r"#token=([A-Za-z0-9_-]+)", content.json()["Text"])
                        assert match, "Account link missing from captured email"
                        return match.group(1)
                time.sleep(1)
            raise AssertionError("No captured email; check worker, beat and Mailpit overlay")

        try:
            created = app.post("/users", json={"username": username, "password": password, "email": email})
            created.raise_for_status()
            user_id = created.json()["id"]
            original = login()
            headers = {"Authorization": f"Bearer {original['access_token']}"}
            assert app.post("/auth/email-verification/request", headers=headers).status_code == 202
            token = read_link("Verify your email")
            assert app.get("/verify-email").status_code == 200
            assert app.post("/auth/email-verification/confirm", json={"token": token}).status_code == 204
            assert app.get("/me", headers=headers).json()["email_verified"] is True
            assert app.post("/auth/email-verification/confirm", json={"token": token}).status_code == 400
            print("Captured verification email and confirmed single-use link: OK", flush=True)
            assert app.get("/me/notifications", headers=headers).json() == {"email_publications": False}
            assert app.patch("/me/notifications", headers=headers, json={"email_publications": True}).status_code == 200
            created_author = app.post("/users", json={"username": author_name, "password": author_password})
            created_author.raise_for_status()
            author_id = created_author.json()["id"]
            author_login = app.post("/login", json={"username": author_name, "password": author_password})
            author_login.raise_for_status()
            author_headers = {"Authorization": f"Bearer {author_login.json()['access_token']}"}
            assert app.post("/subscriptions", headers=headers, json={"author_id": author_id}).status_code == 201
            assert app.post("/posts", headers=author_headers, json={
                "title": "Notification smoke", "content": "Temporary", "is_published": True,
            }).status_code == 201
            assert "Notification smoke" in read_link(f"New post from {author_name}: Notification smoke", token_required=False)
            assert app.patch("/me/notifications", headers=headers, json={"email_publications": False}).status_code == 200
            assert len(app.get("/feed", headers=headers).json()["items"]) == 1
            print("Verified opt-in publication mail, opt-out and unchanged feed: OK", flush=True)
            assert app.post("/auth/password-reset/request", json={"email": email}).status_code == 202
            token = read_link("Reset your password")
            replacement = secrets.token_urlsafe(24)
            assert app.get("/reset-password").status_code == 200
            assert app.post("/auth/password-reset/confirm", json={"token": token, "password": replacement}).status_code == 204
            password = replacement
            assert app.get("/me", headers=headers).status_code == 401
            assert app.post("/refresh", json={"refresh_token": original["refresh_token"]}).status_code == 401
            tokens = login()
            headers = {"Authorization": f"Bearer {tokens['access_token']}"}
            assert app.post("/logout", headers=headers).status_code == 204
            assert app.get("/me", headers=headers).status_code == 401
            print("Captured reset email, changed password, revoked old sessions and logged out: OK", flush=True)
        finally:
            if author_id is not None:
                author_login = app.post("/login", json={"username": author_name, "password": author_password})
                author_login.raise_for_status()
                headers = {"Authorization": f"Bearer {author_login.json()['access_token']}"}
                assert app.delete(f"/users/{author_id}", headers=headers).status_code == 204
            if user_id is not None:
                headers = {"Authorization": f"Bearer {login()['access_token']}"}
                response = app.delete(f"/users/{user_id}", headers=headers)
                assert response.status_code == 204, "Temporary account cleanup failed"
            if message_ids:
                response = mailbox.request("DELETE", "/api/v1/messages", json={"IDs": message_ids})
                response.raise_for_status()


if __name__ == "__main__":
    main()
