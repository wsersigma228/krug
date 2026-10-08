import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# Local defaults; Compose overrides service addresses.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://myuser:1234@localhost:5432/mydb"
)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "change-me":
    raise RuntimeError("Set a non-default SECRET_KEY in .env or the environment")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# An empty host disables email delivery.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "")
_smtp_tls = os.getenv("SMTP_STARTTLS", "true").lower()
if _smtp_tls not in {"true", "false"}:
    raise RuntimeError("SMTP_STARTTLS must be true or false")
SMTP_STARTTLS = _smtp_tls == "true"
if SMTP_USER and not SMTP_STARTTLS:
    raise RuntimeError("SMTP authentication requires STARTTLS")
PUBLIC_APP_URL = os.getenv("PUBLIC_APP_URL", "http://localhost:8000").rstrip("/")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", "media"))
GITLAB_PROJECTS = tuple(name.strip() for name in os.getenv("GITLAB_PROJECTS", "").split(",") if name.strip())
if len(GITLAB_PROJECTS) > 10:
    raise RuntimeError("GITLAB_PROJECTS supports at most 10 projects")
if RATE_LIMIT_PER_MINUTE < 1:
    raise RuntimeError("RATE_LIMIT_PER_MINUTE must be positive")
