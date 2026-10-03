"""Publication mail requires verified, explicit opt-in."""
from alembic import op
import sqlalchemy as sa

revision = "f64d8a013027"
down_revision = "e53b7c902f16"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("email_publications", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("users", "email_publications", server_default=None)
    op.execute("UPDATE email_deliveries SET status = 'cancelled' WHERE kind = 'publication' AND status = 'pending'")


def downgrade():
    op.drop_column("users", "email_publications")
