"""Restore indexes used by feeds and subscriber lookups."""
from alembic import op

revision = "9b61d730e2a4"
down_revision = "4ccc10fdb716"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_posts_author_published_created", "posts", ["author_id", "is_published", "created_at"])
    op.create_index("ix_subscriptions_author_id", "subscriptions", ["author_id"])


def downgrade():
    op.drop_index("ix_subscriptions_author_id", table_name="subscriptions")
    op.drop_index("ix_posts_author_published_created", table_name="posts")
