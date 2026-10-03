"""Keep an explicit account language; existing accounts remain unset."""
from alembic import op
import sqlalchemy as sa

revision = "a75e9b024138"
down_revision = "a71c9e426805"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("language", sa.String(2), nullable=True))
    op.create_check_constraint("ck_users_language", "users", "language IN ('ru', 'en')")


def downgrade():
    op.drop_constraint("ck_users_language", "users", type_="check")
    op.drop_column("users", "language")
