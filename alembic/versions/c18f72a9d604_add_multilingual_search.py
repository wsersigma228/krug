"""Add stored multilingual search vectors and GIN indexes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

revision = "c18f72a9d604"
down_revision = "b437da1c9280"
branch_labels = None
depends_on = None

LANGUAGES = ("simple", "russian", "english")


def upgrade():
    # Keep migration expressions independent of future application changes.
    for language in LANGUAGES:
        expression = (
            f"setweight(to_tsvector('pg_catalog.{language}'::regconfig, coalesce(title, '')), 'A') || "
            f"setweight(to_tsvector('pg_catalog.{language}'::regconfig, coalesce(content, '')), 'B')"
        )
        op.add_column("posts", sa.Column(
            f"search_{language}", TSVECTOR(), sa.Computed(expression, persisted=True),
        ))
        op.create_index(
            f"ix_posts_search_{language}", "posts", [f"search_{language}"],
            postgresql_using="gin",
        )


def downgrade():
    for language in reversed(LANGUAGES):
        op.drop_index(f"ix_posts_search_{language}", table_name="posts")
        op.drop_column("posts", f"search_{language}")
