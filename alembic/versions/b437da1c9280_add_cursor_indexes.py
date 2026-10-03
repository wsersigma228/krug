"""Index the filters and ordering used by cursor pages."""
from alembic import op
import sqlalchemy as sa

revision = "b437da1c9280"
down_revision = "9b61d730e2a4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_posts_author_created_id", "posts", ["author_id", "created_at", "id"])
    op.create_index("ix_posts_author_published_created_id", "posts", ["author_id", "is_published", "created_at", "id"])
    op.create_index("ix_posts_published_created_id", "posts", ["created_at", "id"], postgresql_where=sa.text("is_published IS TRUE"))
    op.create_index("ix_subscriptions_author_created_id", "subscriptions", ["author_id", "created_at", "id"])
    op.create_index("ix_subscriptions_subscriber_created_id", "subscriptions", ["subscriber_id", "created_at", "id"])
    op.drop_index("ix_posts_author_published_created", table_name="posts")
    op.drop_index("ix_subscriptions_author_id", table_name="subscriptions")


def downgrade():
    op.create_index("ix_posts_author_published_created", "posts", ["author_id", "is_published", "created_at"])
    op.create_index("ix_subscriptions_author_id", "subscriptions", ["author_id"])
    op.drop_index("ix_subscriptions_subscriber_created_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_author_created_id", table_name="subscriptions")
    op.drop_index("ix_posts_published_created_id", table_name="posts")
    op.drop_index("ix_posts_author_published_created_id", table_name="posts")
    op.drop_index("ix_posts_author_created_id", table_name="posts")
