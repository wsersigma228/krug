from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator
from backend.schemas import PageParams

from backend.project_schemas import safe_http_url

Format = Literal["online", "local", "hybrid"]
Visibility = Literal["draft", "public"]
Slug = Field(min_length=3, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def text_not_blank(value):
    if not value.strip():
        raise ValueError("Text cannot be blank")
    return value.strip()


def labels(values, limit=20, max_length=50):
    result = list(dict.fromkeys(value.strip().lower() for value in values))
    if len(result) > limit or any(not value or len(value) > max_length for value in result):
        raise ValueError("Invalid labels")
    return result


def normalize_languages(values):
    return labels(values, 10, 20)


def reject_nulls(values, optional=()):
    if isinstance(values, dict) and any(value is None for key, value in values.items() if key not in optional):
        raise ValueError("Omit unchanged fields; fields cannot be null")
    return values


class TeamInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Slug
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=50000)
    skills: list[str] = Field(default_factory=list, max_length=20)
    topics: list[str] = Field(default_factory=list, max_length=20)
    languages: list[str] = Field(default_factory=list, max_length=10)
    format: Format = "online"
    location: str | None = Field(default=None, max_length=160)
    commitment: str | None = Field(default=None, max_length=100)
    visibility: Visibility = "draft"
    status: Literal["recruiting", "active", "archived"] = "recruiting"
    event_id: int | None = Field(default=None, gt=0, le=2_147_483_647)

    _clean_text = field_validator("title", "summary")(text_not_blank)
    _clean_labels = field_validator("skills", "topics")(labels)
    _clean_languages = field_validator("languages")(normalize_languages)


class TeamPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=50000)
    skills: list[str] | None = Field(default=None, max_length=20)
    topics: list[str] | None = Field(default=None, max_length=20)
    languages: list[str] | None = Field(default=None, max_length=10)
    format: Format | None = None
    location: str | None = Field(default=None, max_length=160)
    commitment: str | None = Field(default=None, max_length=100)
    visibility: Visibility | None = None
    status: Literal["recruiting", "active", "archived"] | None = None
    event_id: int | None = Field(default=None, gt=0, le=2_147_483_647)
    _clean_text = field_validator("title", "summary")(text_not_blank)
    _clean_labels = field_validator("skills", "topics")(labels)
    _clean_languages = field_validator("languages")(normalize_languages)
    _reject_nulls = model_validator(mode="before")(lambda values: reject_nulls(values, {"location", "commitment", "event_id"}))


class CommunityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Slug
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=50000)
    topics: list[str] = Field(default_factory=list, max_length=20)
    skills: list[str] = Field(default_factory=list, max_length=20)
    languages: list[str] = Field(default_factory=list, max_length=10)
    format: Format = "online"
    location: str | None = Field(default=None, max_length=160)
    visibility: Visibility = "draft"
    _clean_text = field_validator("title", "summary")(text_not_blank)
    _clean_topics = field_validator("topics", "skills")(labels)
    _clean_languages = field_validator("languages")(normalize_languages)


class CommunityPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=50000)
    topics: list[str] | None = Field(default=None, max_length=20)
    skills: list[str] | None = Field(default=None, max_length=20)
    languages: list[str] | None = Field(default=None, max_length=10)
    format: Format | None = None
    location: str | None = Field(default=None, max_length=160)
    visibility: Visibility | None = None
    _clean_text = field_validator("title", "summary")(text_not_blank)
    _clean_topics = field_validator("topics", "skills")(labels)
    _clean_languages = field_validator("languages")(normalize_languages)
    _reject_nulls = model_validator(mode="before")(lambda values: reject_nulls(values, {"location"}))


EventType = Literal["hackathon", "game_jam", "meetup", "other"]
EventStatus = Literal["scheduled", "active", "ended", "cancelled"]
EventOrigin = Literal["native", "external"]


class EventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Slug
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=50000)
    type: EventType = "other"
    starts_at: AwareDatetime
    ends_at: AwareDatetime | None = None
    deadline: AwareDatetime | None = None
    timezone: str = Field(min_length=1, max_length=100)
    participation_url: str | None = Field(default=None, max_length=2048)
    origin: EventOrigin = "native"
    source_name: str | None = Field(default=None, max_length=40)
    source_url: str | None = Field(default=None, max_length=2048)
    skills: list[str] = Field(default_factory=list, max_length=20)
    topics: list[str] = Field(default_factory=list, max_length=20)
    languages: list[str] = Field(default_factory=list, max_length=10)
    format: Format = "online"
    location: str | None = Field(default=None, max_length=160)
    visibility: Visibility = "draft"
    status: EventStatus = "scheduled"

    _clean_text = field_validator("title", "summary")(text_not_blank)
    _clean_skills = field_validator("skills", "topics")(labels)
    _clean_languages = field_validator("languages")(normalize_languages)
    _safe_urls = field_validator("participation_url", "source_url")(safe_http_url)
    _clean_source_name = field_validator("source_name")(
        lambda value: value.strip() or None if value is not None else None)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Unknown IANA timezone") from None
        return value

    @model_validator(mode="after")
    def time_order(self):
        if self.ends_at is not None and self.ends_at < self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        if self.deadline is not None and self.ends_at is not None and self.deadline > self.ends_at:
            raise ValueError("deadline must be at or before ends_at")
        return self


class EventPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=50000)
    type: EventType | None = None
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None
    deadline: AwareDatetime | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=100)
    participation_url: str | None = Field(default=None, max_length=2048)
    source_name: str | None = Field(default=None, max_length=40)
    source_url: str | None = Field(default=None, max_length=2048)
    skills: list[str] | None = Field(default=None, max_length=20)
    topics: list[str] | None = Field(default=None, max_length=20)
    languages: list[str] | None = Field(default=None, max_length=10)
    format: Format | None = None
    location: str | None = Field(default=None, max_length=160)
    visibility: Visibility | None = None
    status: EventStatus | None = None
    _clean_text = field_validator("title", "summary")(text_not_blank)
    _clean_skills = field_validator("skills", "topics")(labels)
    _clean_languages = field_validator("languages")(normalize_languages)
    _safe_urls = field_validator("participation_url", "source_url")(safe_http_url)
    _clean_source_name = field_validator("source_name")(
        lambda value: value.strip() or None if value is not None else None)
    _reject_nulls = model_validator(mode="before")(lambda values: reject_nulls(
        values, {"ends_at", "deadline", "participation_url", "source_name", "source_url", "location"}))


class TeamParams(PageParams):
    search: str | None = Field(default=None, max_length=100)
    skill: str | None = Field(default=None, max_length=50)
    topic: str | None = Field(default=None, max_length=50)
    language: str | None = Field(default=None, max_length=20)
    format: Format | None = None
    status: Literal["recruiting", "active", "archived"] | None = None
    event_id: int | None = Field(default=None, gt=0)
    saved: bool | None = None


class CommunityParams(PageParams):
    search: str | None = Field(default=None, max_length=100)
    skill: str | None = Field(default=None, max_length=50)
    topic: str | None = Field(default=None, max_length=50)
    language: str | None = Field(default=None, max_length=20)
    format: Format | None = None
    saved: bool | None = None


class EventParams(PageParams):
    search: str | None = Field(default=None, max_length=100)
    skill: str | None = Field(default=None, max_length=50)
    topic: str | None = Field(default=None, max_length=50)
    language: str | None = Field(default=None, max_length=20)
    format: Format | None = None
    status: EventStatus | None = None
    type: EventType | None = None
    upcoming: bool = False
    starts_after: AwareDatetime | None = None
    starts_before: AwareDatetime | None = None
    saved: bool | None = None

    @model_validator(mode="after")
    def date_order(self):
        if self.starts_after and self.starts_before and self.starts_after > self.starts_before:
            raise ValueError("starts_after must be before starts_before")
        return self


class OpeningInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=100)
    skills: list[str] = Field(default_factory=list, max_length=20)
    commitment: str | None = Field(default=None, max_length=100)
    description: str = Field(default="", max_length=5000)
    status: Literal["open", "closed"] = "open"
    _clean_text = field_validator("title", "role")(text_not_blank)
    _clean_skills = field_validator("skills")(labels)


class OpeningPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=100)
    role: str | None = Field(default=None, min_length=1, max_length=100)
    skills: list[str] | None = Field(default=None, max_length=20)
    commitment: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=5000)
    status: Literal["open", "closed"] | None = None
    _clean_text = field_validator("title", "role")(text_not_blank)
    _clean_skills = field_validator("skills")(labels)
    _reject_nulls = model_validator(mode="before")(lambda values: reject_nulls(values, {"commitment"}))


class ApplicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=5000)
    _clean_message = field_validator("message")(text_not_blank)


class ApplicationStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["accepted", "rejected", "withdrawn"]


class EngagementPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    saved: StrictBool | None = None
    interested: StrictBool | None = None
    interested_visible: StrictBool | None = None
    _reject_nulls = model_validator(mode="before")(reject_nulls)


class SavePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    saved: StrictBool


class EntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    title: str
    summary: str
    description: str
    owner_id: int | None
    visibility: Visibility
    cover_url: str | None
    created_at: datetime
    updated_at: datetime


class TeamResponse(EntityResponse):
    skills: list[str]
    topics: list[str]
    languages: list[str]
    format: Format
    location: str | None
    commitment: str | None
    status: Literal["recruiting", "active", "archived"]
    event_id: int | None
    linked_project_id: int | None
    member_count: int = 0
    openings_count: int = 0
    interested_count: int = 0
    saved: bool = False
    interested: bool = False
    interested_visible: bool = False
    is_member: bool = False


class CommunityResponse(EntityResponse):
    topics: list[str]
    skills: list[str]
    languages: list[str]
    format: Format
    location: str | None
    member_count: int = 0
    published_posts_count: int = 0
    saved: bool = False
    is_member: bool = False


class EventResponse(EntityResponse):
    type: EventType
    starts_at: AwareDatetime
    ends_at: AwareDatetime | None
    deadline: AwareDatetime | None
    timezone: str
    participation_url: str | None
    source_url: str | None
    origin: EventOrigin
    source_name: str | None
    source_external_id: str | None
    canonical_url: str | None
    skills: list[str]
    topics: list[str]
    languages: list[str]
    format: Format
    location: str | None
    status: EventStatus
    interested_count: int = 0
    saved: bool = False
    interested: bool = False
    interested_visible: bool = False


class MemberResponse(BaseModel):
    id: int
    user_id: int
    username: str
    display_name: str
    avatar_url: str | None = None
    role: str | None = None
    joined_at: datetime


class OpeningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    team_id: int
    title: str
    role: str
    skills: list[str]
    commitment: str | None
    description: str
    status: str
    created_at: datetime
    updated_at: datetime


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    opening_id: int
    applicant_id: int
    message: str
    status: str
    created_at: datetime
    updated_at: datetime
