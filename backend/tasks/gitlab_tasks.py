import asyncio

from backend.gitlab_import import run_import
from backend.tasks.celery_app import celery_app


@celery_app.task(name="backend.tasks.gitlab_tasks.import_gitlab")
def import_gitlab():
    return asyncio.run(run_import())
