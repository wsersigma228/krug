"""Add teams, communities, events, and community posts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "db71e945ac30"
down_revision = "c4e8d1a9b210"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False), sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("type", sa.String(12), nullable=False, server_default="other"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True)), sa.Column("deadline", sa.DateTime(timezone=True)),
        sa.Column("timezone", sa.String(100), nullable=False), sa.Column("participation_url", sa.String(2048)),
        sa.Column("origin", sa.String(10), nullable=False, server_default="native"),
        sa.Column("source_name", sa.String(40)), sa.Column("source_external_id", sa.String(200)),
        sa.Column("canonical_url", sa.String(2048)), sa.Column("source_url", sa.String(2048)),
        sa.Column("skills", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("topics", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("languages", postgresql.ARRAY(sa.String(20)), nullable=False, server_default="{}"),
        sa.Column("format", sa.String(10), nullable=False, server_default="online"), sa.Column("location", sa.String(160)),
        sa.Column("visibility", sa.String(10), nullable=False, server_default="draft"),
        sa.Column("status", sa.String(12), nullable=False, server_default="scheduled"),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("cover_key", sa.String(40)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("search_vector", postgresql.TSVECTOR(), sa.Computed(
            "setweight(to_tsvector('pg_catalog.simple'::regconfig, coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('pg_catalog.simple'::regconfig, coalesce(summary, '') || ' ' || coalesce(description, '')), 'B')",
            persisted=True)),
        sa.CheckConstraint("origin IN ('native', 'external')", name="ck_events_origin"),
        sa.CheckConstraint("origin <> 'native' OR owner_id IS NOT NULL", name="ck_events_native_owner"),
        sa.CheckConstraint("type IN ('hackathon', 'game_jam', 'meetup', 'other')", name="ck_events_type"),
        sa.CheckConstraint("status IN ('scheduled', 'active', 'ended', 'cancelled')", name="ck_events_status"),
        sa.CheckConstraint("visibility IN ('draft', 'public')", name="ck_events_visibility"),
        sa.CheckConstraint("format IN ('online', 'local', 'hybrid')", name="ck_events_format"),
        sa.CheckConstraint("ends_at IS NULL OR ends_at >= starts_at", name="ck_events_time_order"),
        sa.CheckConstraint("deadline IS NULL OR ends_at IS NULL OR deadline <= ends_at", name="ck_events_deadline_order"),
        sa.UniqueConstraint("source_name", "source_external_id", name="uq_events_source_id"),
        sa.UniqueConstraint("canonical_url", name="uq_events_canonical_url"))
    op.create_index("ix_events_owner_id", "events", ["owner_id"])
    op.create_index("ix_events_public_start", "events", ["starts_at", "id"], postgresql_where=sa.text("visibility = 'public' AND status IN ('scheduled', 'active')"))
    op.create_index("ix_events_search", "events", ["search_vector"], postgresql_using="gin")
    for name, column in (("ix_events_skills", "skills"), ("ix_events_topics", "topics"), ("ix_events_languages", "languages")):
        op.create_index(name, "events", [column], postgresql_using="gin")

    op.create_table("teams",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False), sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("skills", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("topics", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("languages", postgresql.ARRAY(sa.String(20)), nullable=False, server_default="{}"),
        sa.Column("format", sa.String(10), nullable=False, server_default="online"),
        sa.Column("location", sa.String(160)), sa.Column("commitment", sa.String(100)),
        sa.Column("visibility", sa.String(10), nullable=False, server_default="draft"),
        sa.Column("status", sa.String(12), nullable=False, server_default="recruiting"),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cover_key", sa.String(40)),
        sa.Column("linked_project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="SET NULL"), unique=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("search_vector", postgresql.TSVECTOR(), sa.Computed(
            "setweight(to_tsvector('pg_catalog.simple'::regconfig, coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('pg_catalog.simple'::regconfig, coalesce(summary, '') || ' ' || coalesce(description, '')), 'B')",
            persisted=True)),
        sa.CheckConstraint("status IN ('recruiting', 'active', 'archived')", name="ck_teams_status"),
        sa.CheckConstraint("visibility IN ('draft', 'public')", name="ck_teams_visibility"),
        sa.CheckConstraint("format IN ('online', 'local', 'hybrid')", name="ck_teams_format"))
    op.create_index("ix_teams_owner_id", "teams", ["owner_id"])
    op.create_index("ix_teams_event_id", "teams", ["event_id"])
    op.create_index("ix_teams_public_created_id", "teams", ["created_at", "id"], postgresql_where=sa.text("visibility = 'public' AND status <> 'archived'"))
    op.create_index("ix_teams_search", "teams", ["search_vector"], postgresql_using="gin")
    op.create_index("ix_teams_skills", "teams", ["skills"], postgresql_using="gin")
    op.create_index("ix_teams_topics", "teams", ["topics"], postgresql_using="gin")
    op.create_index("ix_teams_languages", "teams", ["languages"], postgresql_using="gin")
    op.create_table("team_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(100), nullable=False, server_default="Member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_member"))
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"])
    op.create_table("team_openings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(100), nullable=False), sa.Column("role", sa.String(100), nullable=False),
        sa.Column("skills", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("commitment", sa.String(100)), sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(10), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_team_opening_status"))
    op.create_index("ix_team_openings_team_status", "team_openings", ["team_id", "status", "id"])
    op.create_table("team_applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("opening_id", sa.Integer(), sa.ForeignKey("team_openings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("applicant_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("opening_id", "applicant_id", name="uq_team_opening_applicant"),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'rejected', 'withdrawn')", name="ck_team_application_status"))
    op.create_index("ix_team_applications_applicant_id", "team_applications", ["applicant_id"])
    op.create_table("team_engagements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("saved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("interested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("interested_visible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_engagement_user"),
        sa.CheckConstraint("NOT interested_visible OR interested", name="ck_team_engagement_visible_interest"))
    op.create_index("ix_team_engagements_user_id", "team_engagements", ["user_id"])

    op.create_table("communities",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False), sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("topics", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("skills", postgresql.ARRAY(sa.String(50)), nullable=False, server_default="{}"),
        sa.Column("languages", postgresql.ARRAY(sa.String(20)), nullable=False, server_default="{}"),
        sa.Column("format", sa.String(10), nullable=False, server_default="online"), sa.Column("location", sa.String(160)),
        sa.Column("visibility", sa.String(10), nullable=False, server_default="draft"),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cover_key", sa.String(40)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("search_vector", postgresql.TSVECTOR(), sa.Computed(
            "setweight(to_tsvector('pg_catalog.simple'::regconfig, coalesce(title, '')), 'A') || "
            "setweight(to_tsvector('pg_catalog.simple'::regconfig, coalesce(summary, '') || ' ' || coalesce(description, '')), 'B')",
            persisted=True)),
        sa.CheckConstraint("visibility IN ('draft', 'public')", name="ck_communities_visibility"),
        sa.CheckConstraint("format IN ('online', 'local', 'hybrid')", name="ck_communities_format"))
    op.create_index("ix_communities_owner_id", "communities", ["owner_id"])
    op.create_index("ix_communities_public_created_id", "communities", ["created_at", "id"], postgresql_where=sa.text("visibility = 'public'"))
    op.create_index("ix_communities_search", "communities", ["search_vector"], postgresql_using="gin")
    op.create_index("ix_communities_topics", "communities", ["topics"], postgresql_using="gin")
    op.create_index("ix_communities_skills", "communities", ["skills"], postgresql_using="gin")
    op.create_index("ix_communities_languages", "communities", ["languages"], postgresql_using="gin")
    op.create_table("community_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("community_id", sa.Integer(), sa.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("community_id", "user_id", name="uq_community_member"))
    op.create_index("ix_community_members_user_id", "community_members", ["user_id"])
    op.create_table("community_engagements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("community_id", sa.Integer(), sa.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("saved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("community_id", "user_id", name="uq_community_engagement_user"))
    op.create_index("ix_community_engagements_user_id", "community_engagements", ["user_id"])

    op.create_table("event_engagements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("saved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("interested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("interested_visible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("event_id", "user_id", name="uq_event_engagement_user"),
        sa.CheckConstraint("NOT interested_visible OR interested", name="ck_event_engagement_visible_interest"))
    op.create_index("ix_event_engagements_user_id", "event_engagements", ["user_id"])

    op.add_column("users", sa.Column("avatar_key", sa.String(40), nullable=True))
    op.add_column("projects", sa.Column("languages", postgresql.ARRAY(sa.String(20)), nullable=False, server_default="{}"))
    op.add_column("projects", sa.Column("format", sa.String(12), nullable=False, server_default="unspecified"))
    op.create_check_constraint("ck_projects_format", "projects", "format IN ('unspecified', 'online', 'local', 'hybrid')")
    op.add_column("projects", sa.Column("location", sa.String(160), nullable=True))
    op.add_column("projects", sa.Column("cover_key", sa.String(40), nullable=True))
    op.create_index("ix_projects_languages", "projects", ["languages"], postgresql_using="gin")
    op.add_column("posts", sa.Column("community_id", sa.Integer(), sa.ForeignKey("communities.id", ondelete="RESTRICT"), nullable=True))
    op.create_index("ix_posts_community_id", "posts", ["community_id"])
    op.create_check_constraint("ck_posts_one_owner_entity", "posts", "NOT (project_id IS NOT NULL AND community_id IS NOT NULL)")


def downgrade():
    op.drop_constraint("ck_posts_one_owner_entity", "posts", type_="check")
    op.drop_index("ix_posts_community_id", table_name="posts")
    op.drop_column("posts", "community_id")
    op.drop_index("ix_projects_languages", table_name="projects")
    op.drop_constraint("ck_projects_format", "projects", type_="check")
    op.drop_column("projects", "location")
    op.drop_column("projects", "cover_key")
    op.drop_column("projects", "format")
    op.drop_column("projects", "languages")
    op.drop_column("users", "avatar_key")
    for name, table in (("ix_events_search", "events"), ("ix_teams_search", "teams"),
                        ("ix_communities_search", "communities")):
        op.drop_index(name, table_name=table)
    for table in ("event_engagements", "community_engagements", "community_members", "team_engagements",
                  "team_applications", "team_openings", "team_members", "teams", "communities", "events"):
        op.drop_table(table)
