import asyncio
from backend.tasks.celery_app import celery_app
from backend.github_import import run_import


@celery_app.task(name="backend.tasks.github_tasks.import_github")
def import_github():
    return asyncio.run(run_import())
