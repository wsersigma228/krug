"""Persist publication emails in the same transaction as posts."""
from alembic import op
import sqlalchemy as sa

revision = "d42c6a891e05"
down_revision = "c18f72a9d604"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "email_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("publication_id", sa.String(36), nullable=False),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.String(100), nullable=True),
        sa.UniqueConstraint("publication_id", "recipient_id", name="uq_email_publication_recipient"),
        sa.CheckConstraint("status IN ('pending', 'sent', 'failed', 'cancelled')", name="ck_email_delivery_status"),
    )
    op.create_index("ix_email_pending_due", "email_deliveries", ["available_at", "id"],
                    postgresql_where=sa.text("status = 'pending'"))


def downgrade():
    op.drop_table("email_deliveries")
