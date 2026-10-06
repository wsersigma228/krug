from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from backend.database import Base
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint, CheckConstraint, Index, text, Computed
from sqlalchemy.dialects.postgresql import TSVECTOR, ARRAY
from sqlalchemy.orm import deferred


def search_column(language: str):
    # PostgreSQL refreshes the stored vector on every text edit.
    expression = (
        f"setweight(to_tsvector('pg_catalog.{language}'::regconfig, coalesce(title, '')), 'A') || "
        f"setweight(to_tsvector('pg_catalog.{language}'::regconfig, coalesce(content, '')), 'B')"
    )
    return deferred(Column(TSVECTOR, Computed(expression, persisted=True)))


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        Index("ix_posts_search_simple", "search_simple", postgresql_using="gin"),
        Index("ix_posts_search_russian", "search_russian", postgresql_using="gin"),
        Index("ix_posts_search_english", "search_english", postgresql_using="gin"),
        Index("ix_posts_author_created_id", "author_id", "created_at", "id"),
        Index(
            "ix_posts_author_published_created_id",
            "author_id", "is_published", "created_at", "id",
        ),
        Index(
            "ix_posts_published_created_id", "created_at", "id",
            postgresql_where=text("is_published IS TRUE"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    search_simple = search_column("simple")
    search_russian = search_column("russian")
    search_english = search_column("english")
    is_published = Column(Boolean, default=False, nullable=False)
    image_key = Column(String(40), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    author = relationship("User", back_populates="posts")

    @property
    def image_url(self):
        return f"/posts/{self.id}/image?v={self.image_key}" if self.image_key else None


class Subscription(Base):
    __tablename__ = "subscriptions"

    __table_args__ = (
        Index("ix_subscriptions_author_created_id", "author_id", "created_at", "id"),
        Index("ix_subscriptions_subscriber_created_id", "subscriber_id", "created_at", "id"),
        UniqueConstraint(
            "subscriber_id",
            "author_id",
            name="uq_subscriber_author",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Both sides reference users; foreign_keys disambiguates the joins.
    subscriber = relationship("User", foreign_keys=[subscriber_id], back_populates="subscriptions")
    author = relationship("User", foreign_keys=[author_id], back_populates="subscribers")


class EmailDelivery(Base):
    __tablename__ = "email_deliveries"
    __table_args__ = (
        UniqueConstraint("publication_id", "recipient_id", name="uq_email_publication_recipient"),
        CheckConstraint("status IN ('pending', 'sent', 'failed', 'cancelled')", name="ck_email_delivery_status"),
        CheckConstraint("(kind = 'publication' AND post_id IS NOT NULL AND publication_id IS NOT NULL AND token_id IS NULL) OR (kind IN ('verify', 'reset') AND post_id IS NULL AND publication_id IS NULL AND token_id IS NOT NULL)", name="ck_email_delivery_kind"),
        Index("ix_email_pending_due", "available_at", "id", postgresql_where=text("status = 'pending'")),
    )

    id = Column(Integer, primary_key=True)
    kind = Column(String(12), default="publication", nullable=False)
    publication_id = Column(String(36), nullable=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    token_id = Column(String(64), ForeignKey("account_tokens.token_hash", ondelete="CASCADE"), unique=True, nullable=True)
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(10), default="pending", nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    available_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_error = Column(String(100), nullable=True)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("language IN ('ru', 'en')", name="ck_users_language"),)

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    email_publications = Column(Boolean, default=False, nullable=False)
    token_version = Column(Integer, default=0, nullable=False)
    display_name = Column(String(100), default="", nullable=False)
    bio = Column(String(500), default="", nullable=False)
    language = Column(String(2), nullable=True)

    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")

    subscriptions = relationship(
        "Subscription",
        foreign_keys=[Subscription.subscriber_id],
        back_populates="subscriber",
        cascade="all, delete-orphan"
    )
    subscribers = relationship(
        "Subscription",
        foreign_keys=[Subscription.author_id],
        back_populates="author",
        cascade="all, delete-orphan"
    )


class AccountToken(Base):
    __tablename__ = "account_tokens"
    __table_args__ = (CheckConstraint("purpose IN ('verify', 'reset')", name="ck_account_token_purpose"),)
    token_hash = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = Column(String(10), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed = Column(Boolean, default=False, nullable=False)
    encrypted_secret = Column(Text, nullable=True)


class AuthRateLimit(Base):
    __tablename__ = "auth_rate_limits"
    key = Column(String(64), primary_key=True)
    bucket = Column(Integer, primary_key=True)
    count = Column(Integer, nullable=False)


class Like(Base):
    __tablename__ = "likes"
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (Index("ix_comments_post_created_id", "post_id", "created_at", "id"),)
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("origin IN ('native', 'external')", name="ck_projects_origin"),
        CheckConstraint("origin <> 'native' OR owner_id IS NOT NULL", name="ck_projects_native_owner"),
        CheckConstraint("status IN ('active', 'paused', 'completed', 'archived', 'stale')", name="ck_projects_status"),
        CheckConstraint("stage IN ('unknown', 'idea', 'prototype', 'building', 'shipped')", name="ck_projects_stage"),
        CheckConstraint("recruitment_status IN ('unknown', 'open', 'closed')", name="ck_projects_recruitment"),
        CheckConstraint("visibility IN ('draft', 'public')", name="ck_projects_visibility"),
        UniqueConstraint("source_name", "source_external_id", name="uq_projects_source_id"),
        Index("ix_projects_public_created_id", "created_at", "id", postgresql_where=text("visibility = 'public'")),
        Index("ix_projects_search", "search_vector", postgresql_using="gin"),
        Index("ix_projects_tags", "tags", postgresql_using="gin"),
        Index("ix_projects_skills", "skills", postgresql_using="gin"),
    )
    id = Column(Integer, primary_key=True)
    slug = Column(String(100), nullable=False, unique=True)
    title = Column(String(200), nullable=False)
    summary = Column(String(500), nullable=False)
    description = Column(Text, nullable=False, default="")
    origin = Column(String(10), nullable=False, default="native")
    status = Column(String(12), nullable=False, default="active")
    stage = Column(String(12), nullable=False, default="idea")
    visibility = Column(String(10), nullable=False, default="draft")
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)
    tags = Column(ARRAY(String(50)), nullable=False, default=list)
    skills = Column(ARRAY(String(50)), nullable=False, default=list)
    recruitment_status = Column(String(10), nullable=False, default="unknown")
    commitment = Column(String(100), nullable=True)
    experience_level = Column(String(50), nullable=True)
    source_name = Column(String(40), nullable=True)
    source_url = Column(String(2048), nullable=True)
    source_external_id = Column(String(200), nullable=True)
    canonical_url = Column(String(2048), nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_activity_at = Column(DateTime(timezone=True), nullable=True)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    search_vector = deferred(Column(TSVECTOR, Computed(
        "setweight(to_tsvector('pg_catalog.simple'::regconfig, coalesce(title, '')), 'A') || "
        "setweight(to_tsvector('pg_catalog.simple'::regconfig, coalesce(summary, '') || ' ' || coalesce(description, '')), 'B')",
        persisted=True)))


class ProjectEngagement(Base):
    __tablename__ = "project_engagements"
    __table_args__ = (
        CheckConstraint("NOT interested_visible OR interested", name="ck_engagement_visible_interest"),
        Index("ix_project_engagements_user_created_id", "user_id", "created_at", "id"),
        UniqueConstraint("project_id", "user_id", name="uq_project_engagement_user"),
    )
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    saved = Column(Boolean, nullable=False, default=False)
    following = Column(Boolean, nullable=False, default=False)
    interested = Column(Boolean, nullable=False, default=False)
    interested_visible = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
