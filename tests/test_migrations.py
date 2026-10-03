from uuid import uuid4

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, delete, inspect, insert, select, text

from backend.config import DATABASE_URL
from backend.database import Base
from backend.models import Post, User


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
