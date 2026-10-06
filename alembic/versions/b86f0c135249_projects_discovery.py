"""Add projects and private per-user engagement without changing existing posts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b86f0c135249"
down_revision = "a75e9b024138"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("display_name", sa.String(100), nullable=False, server_default=""))
    op.alter_column("users", "display_name", server_default=None)
    op.create_table("projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("origin", sa.String(10), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("stage", sa.String(12), nullable=False),
        sa.Column("visibility", sa.String(10), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("tags", postgresql.ARRAY(sa.String(50)), nullable=False),
        sa.Column("skills", postgresql.ARRAY(sa.String(50)), nullable=False),
        sa.Column("recruitment_status", sa.String(10), nullable=False),
        sa.Column("commitment", sa.String(100)),
        sa.Column("experience_level", sa.String(50)),
        sa.Column("source_name", sa.String(40)),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("source_external_id", sa.String(200)),
        sa.Column("canonical_url", sa.String(2048), unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("search_vector", postgresql.TSVECTOR(), sa.Computed(
            "setweight(to_tsvector('pg_catalog.simple'::regconfig, coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('pg_catalog.simple'::regconfig, coalesce(summary, '') || ' ' || coalesce(description, '')), 'B')", persisted=True)),
        sa.CheckConstraint("origin IN ('native', 'external')", name="ck_projects_origin"),
        sa.CheckConstraint("origin <> 'native' OR owner_id IS NOT NULL", name="ck_projects_native_owner"),
        sa.CheckConstraint("status IN ('active', 'paused', 'completed', 'archived', 'stale')", name="ck_projects_status"),
        sa.CheckConstraint("stage IN ('unknown', 'idea', 'prototype', 'building', 'shipped')", name="ck_projects_stage"),
        sa.CheckConstraint("visibility IN ('draft', 'public')", name="ck_projects_visibility"),
        sa.CheckConstraint("recruitment_status IN ('unknown', 'open', 'closed')", name="ck_projects_recruitment"),
        sa.UniqueConstraint("source_name", "source_external_id", name="uq_projects_source_id"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_index("ix_projects_public_created_id", "projects", ["created_at", "id"], postgresql_where=sa.text("visibility = 'public'"))
    for column in ("search_vector", "tags", "skills"):
        name = "ix_projects_search" if column == "search_vector" else f"ix_projects_{column}"
        op.create_index(name, "projects", [column], postgresql_using="gin")
    op.add_column("posts", sa.Column("project_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_posts_project_id", "posts", "projects", ["project_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_posts_project_id", "posts", ["project_id"])
    op.create_table("project_engagements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("saved", sa.Boolean(), nullable=False),
        sa.Column("following", sa.Boolean(), nullable=False),
        sa.Column("interested", sa.Boolean(), nullable=False),
        sa.Column("interested_visible", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_engagement_user"),
        sa.CheckConstraint("NOT interested_visible OR interested", name="ck_engagement_visible_interest"),
    )
    op.create_index("ix_project_engagements_user_created_id", "project_engagements", ["user_id", "created_at", "id"])


def downgrade():
    # Old code cannot preserve new project data; operators should roll code forward.
    op.drop_table("project_engagements")
    op.drop_index("ix_posts_project_id", table_name="posts")
    op.drop_constraint("fk_posts_project_id", "posts", type_="foreignkey")
    op.drop_column("posts", "project_id")
    op.drop_table("projects")
    op.drop_column("users", "display_name")
