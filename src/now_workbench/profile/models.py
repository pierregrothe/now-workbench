# src/now_workbench/profile/models.py
# Pydantic models for a signed-in user's profile and avatar.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Models for per-user profiles (the email comes from Cloudflare Access)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["AvatarPublic", "PresetRequest", "ProfilePublic", "ProfileRecord", "ProfileUpdate"]

AvatarKind = Literal["none", "preset", "upload"]


class ProfileRecord(BaseModel):
    """Profile row as stored, keyed by the verified email."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    email: str
    display_name: str = ""
    avatar_kind: AvatarKind = "none"
    avatar_preset: str | None = None
    avatar_updated_at: str | None = None


class AvatarPublic(BaseModel):
    """Avatar description sent to the UI."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: AvatarKind
    preset: str | None = None
    url: str | None = None


class ProfilePublic(BaseModel):
    """The signed-in user's profile together with who they are and what they may do."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    email: str
    display_name: str
    roles: list[str]
    auth_mode: Literal["cloudflare", "local"]
    avatar: AvatarPublic


class ProfileUpdate(BaseModel):
    """Editable profile fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    display_name: str = Field(default="", max_length=80)

    @field_validator("display_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        return value.strip()


class PresetRequest(BaseModel):
    """Choose one of the built-in avatars."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    preset: str
