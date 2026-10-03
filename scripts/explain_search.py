"""Measure search on temporary data; never modify application posts."""
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from backend.search import search_statement


def main():
    url = os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://myuser:1234@localhost:5432/test_db")
    if make_url(url).database != "test_db":
        raise RuntimeError("Search benchmarks require test_db")
    engine = create_engine(url.replace("psycopg_async", "psycopg"))
    with engine.connect() as connection:
        # The temporary table shadows public.posts only on this connection.
        connection.exec_driver_sql("CREATE TEMP TABLE posts (LIKE public.posts INCLUDING ALL)")
        connection.exec_driver_sql("""
            INSERT INTO posts (id, author_id, title, content, is_published, created_at, updated_at)
            SELECT n, mod(n, 30) + 1,
                   CASE WHEN mod(n, 200) = 0 THEN 'quartz кошки running' ELSE 'Notes' END,
                   repeat('Common content about software. ', 20),
                   true, now() - n * interval '1 second', now()
            FROM generate_series(1, 30000) AS n
        """)
        connection.exec_driver_sql("ANALYZE posts")
        print("Temporary dataset: 30,000 posts, 30 authors, 150 rare matches globally.")
        print("\nBaseline: title/content ILIKE, chronological order (different search semantics)")
        plan = connection.exec_driver_sql("""
            EXPLAIN (ANALYZE, BUFFERS)
            SELECT id, title, content FROM posts
            WHERE author_id = 1 AND (title ILIKE '%%quartz%%' OR content ILIKE '%%quartz%%')
            ORDER BY created_at DESC, id DESC LIMIT 21
        """)
        print("\n".join(row[0] for row in plan))
        for language, term in (("simple", "quartz"), ("russian", "кошка"),
                               ("english", "run"), ("simple", "common")):
            print(f"\nFTS language={language}, term={term}")
            statement = search_statement(1, term, language, limit=20)
            compiled = statement.compile(dialect=connection.dialect)
            plan = connection.exec_driver_sql(
                "EXPLAIN (ANALYZE, BUFFERS) " + str(compiled), compiled.params,
            )
            print("\n".join(row[0] for row in plan))
        connection.rollback()
    engine.dispose()


if __name__ == "__main__":
    main()
