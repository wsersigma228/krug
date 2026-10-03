"""Public biographies, post photos, likes and flat comments."""
from alembic import op
import sqlalchemy as sa

revision = "a71c9e426805"
down_revision = "f64d8a013027"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("bio", sa.String(500), nullable=False, server_default=""))
    op.alter_column("users", "bio", server_default=None)
    op.add_column("posts", sa.Column("image_key", sa.String(40), nullable=True))
    op.create_table("likes",
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True))
    op.create_table("comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_comments_post_created_id", "comments", ["post_id", "created_at", "id"])


def downgrade():
    op.drop_table("comments")
    op.drop_table("likes")
    op.drop_column("posts", "image_key")
    op.drop_column("users", "bio")
