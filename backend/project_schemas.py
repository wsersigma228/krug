from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator
from backend.schemas import PageParams

Status = Literal["active", "paused", "completed", "archived", "stale"]
Stage = Literal["unknown", "idea", "prototype", "building", "shipped"]


def safe_http_url(value):
    if value is not None:
        from urllib.parse import urlsplit
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            raise ValueError("Use an HTTP(S) URL without credentials")
    return value


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
    derived_from_project_id: int | None = Field(default=None, gt=0, le=2_147_483_647)

    @field_validator("source_url")
    @classmethod
    def safe_url(cls, value):
        return safe_http_url(value)

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


IntentKind = Literal["looking_for_teammates", "looking_for_project", "open_to_collaboration", "interested_in_event"]


class CollaborationProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skills: list[str] = Field(default_factory=list, max_length=30)
    interests: list[str] = Field(default_factory=list, max_length=30)
    wanted_skills: list[str] = Field(default_factory=list, max_length=30)
    intent_kind: IntentKind | None = None
    intent_text: str | None = Field(default=None, max_length=500)
    timezone: str | None = Field(default=None, max_length=100)
    commitment: str | None = Field(default=None, max_length=100)
    discoverable: bool = False
    status: Literal["active", "paused"] = "active"
    languages: list[str] = Field(default_factory=list, max_length=10)
    external_links: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("skills", "interests", "wanted_skills")
    @classmethod
    def normalize_profile_labels(cls, values):
        values = list(dict.fromkeys(v.strip().lower() for v in values))
        if any(not v or len(v) > 50 for v in values):
            raise ValueError("Labels must contain 1 to 50 characters")
        return values

    @field_validator("languages")
    @classmethod
    def normalize_languages(cls, values):
        values = list(dict.fromkeys(v.strip().lower() for v in values))
        if any(not v or len(v) > 20 for v in values):
            raise ValueError("Language labels must contain 1 to 20 characters")
        return values

    @field_validator("external_links")
    @classmethod
    def safe_links(cls, values):
        for value in values:
            if len(value) > 2048:
                raise ValueError("Links must be at most 2048 characters")
            safe_http_url(value)
        return values

    @model_validator(mode="after")
    def require_intent_for_discovery(self):
        if self.discoverable and self.status == "active" and self.intent_kind is None:
            raise ValueError("Choose an intent before enabling discovery")
        return self


class CollaborationProfileResponse(CollaborationProfileInput):
    user_id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicPerson(BaseModel):
    id: int
    username: str
    display_name: str
    bio: str
    skills: list[str]
    interests: list[str]
    wanted_skills: list[str]
    intent_kind: IntentKind | None
    intent_text: str | None
    timezone: str | None
    commitment: str | None
    languages: list[str]
    external_links: list[str]
    updated_at: datetime
    owned_projects: list[dict]
    memberships: list[dict]


class PeopleParams(PageParams):
    search: str | None = Field(default=None, max_length=100)
    skill: str | None = Field(default=None, max_length=50)
    wanted_skill: str | None = Field(default=None, max_length=50)
    intent_kind: IntentKind | None = None


class DiscoveryProjectResponse(ProjectResponse):
    interested_count: int = 0
    member_count: int = 0
    open_roles_count: int = 0
    published_updates_count: int = 0


class OpeningInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=100)
    skills: list[str] = Field(default_factory=list, max_length=20)
    commitment: str | None = Field(default=None, max_length=100)
    timezone: str | None = Field(default=None, max_length=100)
    experience_level: str | None = Field(default=None, max_length=50)
    description: str = Field(default="", max_length=5000)
    status: Literal["open", "closed"] = "open"

    @field_validator("title", "role")
    @classmethod
    def clean_role_text(cls, value):
        if not value.strip():
            raise ValueError("Text cannot be blank")
        return value.strip()

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, values):
        values = list(dict.fromkeys(value.strip().lower() for value in values))
        if any(not value or len(value) > 50 for value in values):
            raise ValueError("Skills must contain 1 to 50 characters")
        return values


class OpeningPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=100)
    role: str | None = Field(default=None, min_length=1, max_length=100)
    skills: list[str] | None = Field(default=None, max_length=20)
    commitment: str | None = Field(default=None, max_length=100)
    timezone: str | None = Field(default=None, max_length=100)
    experience_level: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=5000)
    status: Literal["open", "closed"] | None = None

    @field_validator("title", "role")
    @classmethod
    def clean_role_text(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Text cannot be blank")
        return value.strip() if value is not None else None

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, values):
        if values is None:
            return values
        values = list(dict.fromkeys(value.strip().lower() for value in values))
        if any(not value or len(value) > 50 for value in values):
            raise ValueError("Skills must contain 1 to 50 characters")
        return values

    @model_validator(mode="before")
    @classmethod
    def reject_null_required(cls, values):
        if isinstance(values, dict) and any(key in values and values[key] is None
                                             for key in ("title", "role", "skills", "description", "status")):
            raise ValueError("Omit unchanged fields; these fields cannot be null")
        return values


class OpeningProject(BaseModel):
    slug: str
    title: str
    summary: str
    model_config = ConfigDict(from_attributes=True)


class OpeningResponse(OpeningInput):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime
    project: OpeningProject | None = None
    model_config = ConfigDict(from_attributes=True)


class OpeningSearchParams(PageParams):
    search: str | None = Field(default=None, max_length=100)
    skill: str | None = Field(default=None, max_length=50)


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=5000)
    applicant_contact_url: str | None = Field(default=None, max_length=2048)

    @field_validator("applicant_contact_url")
    @classmethod
    def safe_url(cls, value):
        return safe_http_url(value)

    @field_validator("message")
    @classmethod
    def nonblank_message(cls, value):
        if not value.strip():
            raise ValueError("Message cannot be blank")
        return value.strip()


class ApplicationStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["accepted", "rejected"]


class ProjectApplicationResponse(BaseModel):
    id: int
    opening_id: int
    applicant_id: int
    applicant_username: str
    project_slug: str
    project_title: str
    opening_title: str
    role: str
    message: str
    status: Literal["pending", "accepted", "rejected", "withdrawn"]
    created_at: datetime
    updated_at: datetime
    applicant_contact_url: str | None = None
    owner_contact_url: str | None = None


class ContactSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    owner_contact_url: str | None = Field(default=None, max_length=2048)

    @field_validator("owner_contact_url")
    @classmethod
    def safe_url(cls, value):
        return safe_http_url(value)


class ExternalSubmissionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=50000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    skills: list[str] = Field(default_factory=list, max_length=20)
    source_url: str = Field(min_length=1, max_length=2048)

    @field_validator("title", "summary")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Text cannot be blank")
        return value.strip()

    @field_validator("tags", "skills")
    @classmethod
    def clean_labels(cls, values):
        return ProjectCreate.labels(values)

    @field_validator("source_url")
    @classmethod
    def safe_url(cls, value):
        return safe_http_url(value)


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["approved", "rejected"]


class ClaimInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_url: str | None = Field(default=None, max_length=2048)
    evidence_text: str | None = Field(default=None, max_length=2000)

    @field_validator("evidence_url")
    @classmethod
    def safe_url(cls, value):
        return safe_http_url(value)

    @model_validator(mode="after")
    def require_evidence(self):
        if not self.evidence_url and not (self.evidence_text and self.evidence_text.strip()):
            raise ValueError("Provide evidence URL or text")
        return self
