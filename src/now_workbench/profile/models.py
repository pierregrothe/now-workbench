# src/now_workbench/profile/models.py
# Pydantic models for the local profile, avatar and email-delivery settings.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Models for the single local user profile (verified by an email code)."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "SERVICENOW_EMAIL_PATTERN",
    "AvatarPublic",
    "CodeConfirm",
    "MailSettings",
    "MailSettingsPublic",
    "MailSettingsUpdate",
    "PresetRequest",
    "ProfileRecord",
    "ProfilePublic",
    "ProfileUpdate",
]

# Exact servicenow.com mailbox; no subdomains, no display names.
SERVICENOW_EMAIL_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._%+-]{0,63}@servicenow\.com$")

AvatarKind = Literal["none", "preset", "upload"]


class ProfileRecord(BaseModel):
    """Profile row as stored, including the pending verification code state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    display_name: str = ""
    email: str = ""
    avatar_kind: AvatarKind = "none"
    avatar_preset: str | None = None
    avatar_updated_at: str | None = None
    email_verified_at: str | None = None
    code_hash: str | None = None
    code_salt: str | None = None
    code_expires_at: str | None = None
    code_attempts: int = 0
    code_sent_at: str | None = None


class AvatarPublic(BaseModel):
    """Avatar description sent to the UI."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: AvatarKind
    preset: str | None = None
    url: str | None = None


class ProfilePublic(BaseModel):
    """Profile as exposed by the API (never the code hash or salt)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    display_name: str
    email: str
    email_verified: bool
    avatar: AvatarPublic
    verification_pending: bool
    mail_configured: bool


class ProfileUpdate(BaseModel):
    """Editable profile fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    display_name: str = Field(default="", max_length=80)
    email: str = Field(default="", max_length=120)

    @field_validator("display_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def _servicenow_mailbox_only(cls, value: str) -> str:
        email = value.strip().lower()
        if email and not SERVICENOW_EMAIL_PATTERN.match(email):
            raise ValueError("Use your active servicenow.com email address.")
        return email


class PresetRequest(BaseModel):
    """Choose one of the built-in avatars."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    preset: str


class CodeConfirm(BaseModel):
    """The code the user received by email."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=4, max_length=32)


class MailSettings(BaseModel):
    """SMTP settings used to deliver verification codes (the password is sealed separately)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    host: str = ""
    port: int = Field(default=587, ge=1, le=65535)
    username: str = ""
    from_address: str = ""
    starttls: bool = True

    @property
    def configured(self) -> bool:
        """True when a host and a sender address are set."""
        return bool(self.host and self.from_address)


class MailSettingsPublic(MailSettings):
    """Mail settings as exposed by the API; the password itself is never returned."""

    has_password: bool = False


class MailSettingsUpdate(MailSettings):
    """Mail settings update; ``password`` None keeps the stored one, '' clears it."""

    password: str | None = Field(default=None, max_length=256)
