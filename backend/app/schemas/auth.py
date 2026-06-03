from datetime import datetime
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import UserApprovalStatus, UserRole
from app.services.user_privacy import (
    build_public_name,
    contains_email_or_phone,
    contains_reserved_display_word,
)

_LOGIN_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def normalize_login(value: str) -> str:
    return value.strip().lower()


def normalize_email(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def normalize_display_name(value: str) -> str:
    return " ".join(value.strip().split())


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=80)
    personal_data_notice_accepted: bool = False
    privacy_notice_version: str = Field(min_length=1, max_length=50)

    @field_validator("login")
    @classmethod
    def _validate_login(cls, value: str) -> str:
        normalized = normalize_login(value)
        if not _LOGIN_RE.match(normalized):
            raise ValueError("Login can contain latin letters, digits, dot, dash and underscore")
        return normalized

    @field_validator("display_name")
    @classmethod
    def _validate_display_name(cls, value: str) -> str:
        normalized = normalize_display_name(value)
        if len(normalized) < 2:
            raise ValueError("Display name is too short")
        if contains_email_or_phone(normalized):
            raise ValueError("Display name must not contain email or phone")
        if contains_reserved_display_word(normalized):
            raise ValueError("Display name must not contain service role words")
        return normalized


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("login")
    @classmethod
    def _normalize_login(cls, value: str) -> str:
        return normalize_login(value)


class UserResponse(BaseModel):
    id: int
    display_name: str
    public_name: str
    email: str | None
    role: UserRole
    approval_status: UserApprovalStatus
    is_active: bool
    must_change_password: bool
    created_at: datetime
    approved_at: datetime | None
    last_login_at: datetime | None

    @classmethod
    def from_user(cls, user) -> "UserResponse":
        return cls(
            id=user.id,
            display_name=user.display_name,
            public_name=build_public_name(user.display_name),
            email=user.email,
            role=user.role,
            approval_status=user.approval_status,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            created_at=user.created_at,
            approved_at=user.approved_at,
            last_login_at=user.last_login_at,
        )


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    token: str
    user: UserResponse


class RegisterResponse(BaseModel):
    user: UserResponse
    message: str


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int


class UserRoleUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: UserRole
