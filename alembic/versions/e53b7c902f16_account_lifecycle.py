"""Account verification, recovery, revocation and request counters."""
from alembic import op
import sqlalchemy as sa

revision = "e53b7c902f16"
down_revision = "d42c6a891e05"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    op.alter_column("users", "email_verified", server_default=None)
    op.alter_column("users", "token_version", server_default=None)
    op.create_table("account_tokens",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(10), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed", sa.Boolean(), nullable=False),
        sa.Column("encrypted_secret", sa.Text(), nullable=True),
        sa.CheckConstraint("purpose IN ('verify', 'reset')", name="ck_account_token_purpose"),
    )
    op.create_index("ix_account_tokens_user_id", "account_tokens", ["user_id"])
    op.create_table("auth_rate_limits",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("bucket", sa.Integer(), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
    )
    op.add_column("email_deliveries", sa.Column("kind", sa.String(12), nullable=False, server_default="publication"))
    op.alter_column("email_deliveries", "kind", server_default=None)
    op.alter_column("email_deliveries", "publication_id", nullable=True)
    op.alter_column("email_deliveries", "post_id", nullable=True)
    op.add_column("email_deliveries", sa.Column("token_id", sa.String(64), nullable=True))
    op.create_foreign_key("fk_email_token", "email_deliveries", "account_tokens", ["token_id"], ["token_hash"], ondelete="CASCADE")
    op.create_unique_constraint("uq_email_token", "email_deliveries", ["token_id"])
    op.create_check_constraint("ck_email_delivery_kind", "email_deliveries",
        "(kind = 'publication' AND post_id IS NOT NULL AND publication_id IS NOT NULL AND token_id IS NULL) OR (kind IN ('verify', 'reset') AND post_id IS NULL AND publication_id IS NULL AND token_id IS NOT NULL)")


def downgrade():
    # Only account-service deliveries belong to the schema being removed.
    op.execute("DELETE FROM email_deliveries WHERE kind <> 'publication'")
    op.drop_constraint("ck_email_delivery_kind", "email_deliveries", type_="check")
    op.drop_constraint("uq_email_token", "email_deliveries", type_="unique")
    op.drop_constraint("fk_email_token", "email_deliveries", type_="foreignkey")
    op.drop_column("email_deliveries", "token_id")
    op.alter_column("email_deliveries", "post_id", nullable=False)
    op.alter_column("email_deliveries", "publication_id", nullable=False)
    op.drop_column("email_deliveries", "kind")
    op.drop_table("auth_rate_limits")
    op.drop_index("ix_account_tokens_user_id", table_name="account_tokens")
    op.drop_table("account_tokens")
    op.drop_column("users", "token_version")
    op.drop_column("users", "email_verified")
