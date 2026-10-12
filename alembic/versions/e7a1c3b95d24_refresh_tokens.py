"""Add server-side refresh token records for rotation and reuse detection."""
from alembic import op
import sqlalchemy as sa

revision = "e7a1c3b95d24"
down_revision = "db71e945ac30"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("refresh_tokens",
        sa.Column("jti", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("family_id", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])


def downgrade():
    op.drop_table("refresh_tokens")
