from celery import Celery
from backend.config import REDIS_URL

celery_app = Celery(
    "blog_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.tasks.email_tasks", "backend.tasks.github_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "refresh-github-projects": {
            "task": "backend.tasks.github_tasks.import_github",
            "schedule": 6 * 60 * 60,
            "options": {"expires": 60 * 60},
        },
        "deliver-pending-emails": {
            "task": "backend.tasks.email_tasks.deliver_pending_emails",
            "schedule": 30.0,
            "options": {"expires": 30},
        },
    },
)
