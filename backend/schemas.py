from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator, StrictBool
from datetime import datetime
from typing import Generic, Optional, TypeVar, Literal


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None
    has_more: bool


class PageParams(BaseModel):
    # Reject old offset requests instead of silently returning page one.
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=100, ge=1, le=100)
    cursor: str | None = Field(default=None, min_length=1, max_length=2048)


class PostPageParams(PageParams):
    is_published: bool | None = None
    search: str | None = Field(default=None, max_length=100)
    search_language: Literal["simple", "russian", "english"] = "simple"


class ExploreParams(PageParams):
    search: str | None = Field(default=None, max_length=100)
    search_language: Literal["simple", "russian", "english"] = "simple"


class PostCreate(BaseModel):
    project_id: int | None = Field(default=None, gt=0)
    title: str = Field(default="", max_length=200)
    content: str = Field(min_length=1)
    is_published: bool = False

    @field_validator("title")
    @classmethod
    def strip_title(cls, value):
        return value.strip()


class PostUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    content: Optional[str] = Field(default=None, min_length=1)
    is_published: Optional[bool] = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value):
        return value.strip()

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_nulls(cls, values):
        if isinstance(values, dict) and any(
            key in values and values[key] is None
            for key in ("title", "content", "is_published")
        ):
            raise ValueError("Post fields cannot be null; omit fields you do not want to update")
        return values


class PostResponse(BaseModel):
    project_id: int | None = None
    id: int
    title: str
    content: str
    is_published: bool
    author_id: int
    created_at: datetime
    updated_at: datetime
    image_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SubscribeRequest(BaseModel):
    author_id: int


class SubscriptionResponse(BaseModel):
    id: int
    subscriber_id: int
    author_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthorWithSubscriptionResponse(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class FeedPostResponse(PostResponse):
    author_username: str


class UserCreate(BaseModel):
    language: Literal["ru", "en"] | None = None
    username: str = Field(min_length=3, max_length=50)
    email: str | None = Field(default=None, max_length=100)
    password: str = Field(min_length=8, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        if value is None:
            return value
        return validate_email_address(value)


class UserResponse(BaseModel):
    display_name: str = ""
    language: Literal["ru", "en"] | None = None
    id: int
    username: str
    email: str | None = None
    role: str
    email_verified: bool = False
    email_publications: bool = False
    bio: str = ""

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=100)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=2048)


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def validate_email_address(value: str) -> str:
    import re
    # Deliberately support ordinary mailbox addresses, not quoted/local-only forms.
    if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}", value):
        raise ValueError("Invalid email address")
    local, domain = value.rsplit("@", 1)
    return f"{local}@{domain.lower()}"


class EmailRequest(BaseModel):
    email: str = Field(min_length=3, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return validate_email_address(value)


class AccountTokenRequest(BaseModel):
    token: str = Field(min_length=1, max_length=128)


class PasswordResetConfirm(AccountTokenRequest):
    password: str = Field(min_length=8, max_length=100)


class NotificationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    email_publications: StrictBool


class LanguageSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    language: Literal["ru", "en"]
