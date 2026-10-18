# 🔒 Security and privacy

> [!NOTE]
> Krug is a work in progress with no production uptime or scale claim. Public
> deployment requires HTTPS, a private environment and your own mail credentials;
> see [development and deployment](docs/development.md#backups-and-public-hosting).

## 📣 Reporting a vulnerability

Use this repository's **private vulnerability reporting** in the Security tab.
Do not post credentials, tokens or private user data in issues or pull requests.

## 🛡️ What the code does

| Area | Behaviour |
| --- | --- |
| Passwords | Argon2 for new hashes, legacy bcrypt still verified; unknown logins still run a dummy hash check to keep timing uniform |
| Access tokens | Short-lived JWT (PyJWT, 30 min by default) in per-tab `sessionStorage`; a per-user token version revokes them all at once |
| Refresh tokens | Only in the `krug_refresh` cookie: `HttpOnly`, `SameSite=Strict`, path `/refresh`, `Secure` when `PUBLIC_APP_URL` is HTTPS. Never sent or accepted in JSON |
| Session theft | Refresh tokens rotate on every use and are stored server-side per login family. Reuse after a 30 s grace window ends every session of that user |
| Rate limits | PostgreSQL-backed per-IP and per-account limits on sign-up, sign-in, refresh, verification, password reset, applications, claims, submissions and content creation (`RATE_LIMIT_PER_MINUTE`) |
| Output | Frontend `html` templates escape values by default; raw markup needs an explicit `SafeHtml`. Server-rendered project share pages send a strict `Content-Security-Policy`; media and share responses send `nosniff` |
| Uploads | JPEG, PNG and WebP up to 8 MB, decoded by Pillow, decompression bombs rejected, EXIF dropped by re-encoding to JPEG |
| Outbound fetches | GitHub and GitLab metadata only, GitLab by explicit allowlist, responses capped at 512 KB |
| Privacy | People are discoverable only by opt-in; saves and follows are private; contacts are shared only after an application is accepted; email is opt-in |
| Runtime | Non-root container image; database, Redis and app ports bound to `127.0.0.1`; `DB_PASSWORD` and `REDIS_PASSWORD` are required; SMTP authentication requires STARTTLS |
| CI | `ruff`, `pip-audit` against pinned `constraints.txt`, the Python test suite and an HTML-escaping check on every push and pull request |

## ⚠️ Known limits

- `sessionStorage` does not protect the access token from XSS. Serve over HTTPS and keep dependencies updated.
- Compose does not provide TLS. Put a reverse proxy in front and set `FORWARDED_ALLOW_IPS` to it; otherwise all clients share the proxy's rate-limit budget. Never use `*` while the app port is reachable directly.
- Rootless Podman can present the container gateway as every client's address, so per-IP limits become shared; per-account limits still apply.
- There is no per-session management screen, broad moderation dashboard or automated backup.

## 🗄️ Data and secrets

- The public repository starts from a reviewed source snapshot with a fresh Git history. Examples, screenshots and automated checks use synthetic accounts and data.
- Local environment files, uploaded media, database dumps and design-tool workspaces are excluded from Git and the container build context. A clean scanner result is not a guarantee that every secret or privacy issue was detected.
- Treat the database, the media volume and the private `.env` as one deployment backup (`./scripts/backup --consistent`). Keep `SECRET_KEY` stable: rotating it signs everyone out and makes queued account-link secrets unreadable.
- If a real credential is ever committed, revoke or rotate it first, then remove it from Git history.
