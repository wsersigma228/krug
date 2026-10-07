"""Add opt-in people discovery, openings and moderated external submissions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c4e8d1a9b210"
down_revision = "b86f0c135249"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("projects", sa.Column("submitted_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.add_column("projects", sa.Column("derived_from_project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True))
    op.add_column("projects", sa.Column("owner_contact_url", sa.String(2048), nullable=True))
    op.add_column("projects", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_projects_submitted_by", "projects", ["submitted_by"])
    op.create_index("ix_projects_derived_from_project_id", "projects", ["derived_from_project_id"])
    op.create_table("collaboration_profiles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("skills", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("interests", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("wanted_skills", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("intent_kind", sa.String(30)), sa.Column("intent_text", sa.String(500)),
        sa.Column("timezone", sa.String(100)), sa.Column("commitment", sa.String(100)),
        sa.Column("discoverable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(10), nullable=False, server_default="active"),
        sa.Column("languages", postgresql.ARRAY(sa.String(20)), nullable=False, server_default="{}"),
        sa.Column("external_links", postgresql.ARRAY(sa.String(2048)), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("intent_kind IS NULL OR intent_kind IN ('looking_for_teammates', 'looking_for_project', 'open_to_collaboration', 'interested_in_event')", name="ck_collab_intent"),
        sa.CheckConstraint("status IN ('active', 'paused')", name="ck_collab_status"))
    op.create_index("ix_collab_discoverable", "collaboration_profiles", ["status", "updated_at"], postgresql_where=sa.text("discoverable IS TRUE"))
    op.create_table("project_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(100), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_member"))
    op.execute("INSERT INTO project_members (project_id, user_id, role, joined_at) SELECT id, owner_id, 'Owner', created_at FROM projects WHERE owner_id IS NOT NULL")
    op.create_table("project_openings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(100), nullable=False), sa.Column("role", sa.String(100), nullable=False),
        sa.Column("skills", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("commitment", sa.String(100)), sa.Column("timezone", sa.String(100)),
        sa.Column("experience_level", sa.String(50)), sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(10), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_opening_status"))
    op.create_index("ix_openings_project_status", "project_openings", ["project_id", "status", "id"])
    op.create_table("project_applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("opening_id", sa.Integer(), sa.ForeignKey("project_openings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("applicant_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False), sa.Column("applicant_contact_url", sa.String(2048)),
        sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("opening_id", "applicant_id", name="uq_opening_applicant"),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'rejected', 'withdrawn')", name="ck_application_status"))
    op.create_table("project_claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_url", sa.String(2048)), sa.Column("evidence_text", sa.String(2000)),
        sa.Column("status", sa.String(10), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_project_claim_status"))
    op.create_table("external_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("submitted_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(200), nullable=False), sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("tags", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("skills", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_external_submission_status"))


def downgrade():
    op.drop_table("external_submissions")
    op.drop_table("project_claims")
    op.drop_table("project_applications")
    op.drop_index("ix_openings_project_status", table_name="project_openings")
    op.drop_table("project_openings")
    op.drop_table("project_members")
    op.drop_index("ix_collab_discoverable", table_name="collaboration_profiles")
    op.drop_table("collaboration_profiles")
    op.drop_index("ix_projects_derived_from_project_id", table_name="projects")
    op.drop_index("ix_projects_submitted_by", table_name="projects")
    op.drop_column("projects", "owner_contact_url")
    op.drop_column("projects", "claimed_at")
    op.drop_column("projects", "derived_from_project_id")
    op.drop_column("projects", "submitted_by")
