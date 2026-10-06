from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator
from backend.schemas import PageParams

Status = Literal["active", "paused", "completed", "archived", "stale"]
Stage = Literal["unknown", "idea", "prototype", "building", "shipped"]


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(min_length=3, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=50000)
    status: Status = "active"
    stage: Stage = "idea"
    visibility: Literal["draft", "public"] = "draft"
    tags: list[str] = Field(default_factory=list, max_length=20)
    skills: list[str] = Field(default_factory=list, max_length=20)
    recruitment_status: Literal["unknown", "open", "closed"] = "unknown"
    commitment: str | None = Field(default=None, max_length=100)
    experience_level: str | None = Field(default=None, max_length=50)
    source_url: str | None = Field(default=None, max_length=2048)

    @field_validator("source_url")
    @classmethod
    def safe_url(cls, value):
        if value is not None:
            from urllib.parse import urlsplit
            parts = urlsplit(value)
            if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
                raise ValueError("Use an HTTP or HTTPS URL without credentials")
        return value

    @field_validator("title", "summary")
    @classmethod
    def text_not_blank(cls, value):
        if not value.strip():
            raise ValueError("Text cannot be blank")
        return value.strip()

    @field_validator("tags", "skills")
    @classmethod
    def labels(cls, values):
        normalized = list(dict.fromkeys(value.strip().lower() for value in values))
        if any(not value or len(value) > 50 for value in normalized):
            raise ValueError("Labels must contain 1 to 50 characters")
        return normalized


class ProjectPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=50000)
    status: Status | None = None
    stage: Stage | None = None
    visibility: Literal["draft", "public"] | None = None
    tags: list[str] | None = Field(default=None, max_length=20)
    skills: list[str] | None = Field(default=None, max_length=20)
    recruitment_status: Literal["unknown", "open", "closed"] | None = None
    commitment: str | None = Field(default=None, max_length=100)
    experience_level: str | None = Field(default=None, max_length=50)
    source_url: str | None = Field(default=None, max_length=2048)
    text_not_blank = field_validator("title", "summary")(ProjectCreate.text_not_blank.__func__)
    labels = field_validator("tags", "skills")(ProjectCreate.labels.__func__)
    safe_url = field_validator("source_url")(ProjectCreate.safe_url.__func__)

    @model_validator(mode="before")
    @classmethod
    def reject_null(cls, values):
        if isinstance(values, dict) and any(value is None for key, value in values.items() if key not in {"commitment", "experience_level", "source_url"}):
            raise ValueError("Omit unchanged fields; fields cannot be null")
        return values


class ProjectResponse(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    origin: Literal["native", "external"]
    owner_id: int | None
    source_name: str | None
    source_url: str | None
    source_external_id: str | None
    canonical_url: str | None
    created_at: datetime
    updated_at: datetime
    last_activity_at: datetime | None
    last_verified_at: datetime | None


class DiscoveryParams(PageParams):
    search: str | None = Field(default=None, max_length=100)
    tag: str | None = Field(default=None, max_length=50)
    skill: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=40)
    status: Status | None = None
    active: bool | None = None
    recruitment_status: Literal["unknown", "open", "closed"] | None = None


class EngagementPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    saved: StrictBool | None = None
    following: StrictBool | None = None
    interested: StrictBool | None = None
    interested_visible: StrictBool | None = None
    reject_null = model_validator(mode="before")(ProjectPatch.reject_null.__func__)


class EngagementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    saved: bool = False
    following: bool = False
    interested: bool = False
    interested_visible: bool = False


class InterestedUser(BaseModel):
    id: int
    username: str
    display_name: str
    bio: str
