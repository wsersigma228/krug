from uuid import uuid4
from datetime import datetime, timezone

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, delete, func, inspect, insert, select, text

from backend.config import DATABASE_URL
from backend.database import Base
from backend.models import Post, Project, ProjectMember, User


def test_cursor_index_migration_round_trip():
    engine = create_engine(DATABASE_URL.replace("psycopg_async", "psycopg"))
    config = Config("alembic.ini")
    with engine.begin() as connection:
        user_id = connection.scalar(insert(User).values(
            username=f"migration_{uuid4().hex}", hashed_password="unused"
        ).returning(User.id))
        post_id = connection.scalar(insert(Post).values(
            author_id=user_id, title="Survives index migration", content="Body", is_published=True
        ).returning(Post.id))
    try:
        command.downgrade(config, "9b61d730e2a4")
        with engine.connect() as connection:
            names = {index["name"] for index in inspect(connection).get_indexes("posts")}
            assert "ix_posts_author_published_created" in names
            assert "ix_posts_published_created_id" not in names
            assert not any(name.startswith("ix_posts_search_") for name in names)
            assert not any(col["name"].startswith("search_") for col in inspect(connection).get_columns("posts"))
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.scalar(select(Post.title).where(Post.id == post_id)) == "Survives index migration"
            for language in ("simple", "russian", "english"):
                assert connection.scalar(text(
                    f"SELECT search_{language} @@ websearch_to_tsquery('pg_catalog.{language}', 'migration') "
                    "FROM posts WHERE id = :id"
                ), {"id": post_id})
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
    finally:
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(delete(Post).where(Post.id == post_id))
            connection.execute(delete(User).where(User.id == user_id))
        engine.dispose()


def test_collaboration_migration_backfills_existing_project_owners():
    engine = create_engine(DATABASE_URL.replace("psycopg_async", "psycopg"))
    config = Config("alembic.ini")
    username = f"migration_owner_{uuid4().hex}"
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        user_id = connection.scalar(insert(User).values(username=username, hashed_password="unused").returning(User.id))
        project_id = connection.scalar(insert(Project).values(
            slug=f"migration-{uuid4().hex[:20]}", title="Old project", summary="Still here",
            description="Before collaboration tables", origin="native", status="active", stage="idea",
            visibility="public", owner_id=user_id, tags=[], skills=[], recruitment_status="unknown",
            created_at=now, updated_at=now,
        ).returning(Project.id))
    try:
        command.downgrade(config, "b86f0c135249")
        command.upgrade(config, "head")
        with engine.connect() as connection:
            memberships = connection.scalar(select(func.count()).select_from(ProjectMember).where(
                ProjectMember.project_id == project_id, ProjectMember.user_id == user_id,
                ProjectMember.role == "Owner"))
            assert memberships == 1
    finally:
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(delete(ProjectMember).where(ProjectMember.project_id == project_id))
            connection.execute(delete(Project).where(Project.id == project_id))
            connection.execute(delete(User).where(User.id == user_id))
        engine.dispose()
