# src/now_workbench/auth/models.py
# Roles and the authenticated user.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Role and user models."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict

__all__ = ["LOCAL_EMAIL", "AuthUser", "Role", "TeamMember"]

LOCAL_EMAIL = "local@localhost"


class Role(StrEnum):
    """What a signed-in person may do."""

    ADMIN = "admin"
    SOLUTION_CONSULTANT = "solution_consultant"


class AuthUser(BaseModel):
    """The person behind a request, as established by Cloudflare Access (or local mode)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    email: str
    roles: frozenset[Role]
    mode: Literal["cloudflare", "local"]
    # Set while an administrator acts as ``email`` (impersonation): who is really signed in.
    real_email: str | None = None
    real_roles: frozenset[Role] = frozenset()

    @property
    def signed_in(self) -> AuthUser:
        """The person actually signed in (themselves when not impersonating)."""
        if self.real_email is None:
            return self
        return AuthUser(email=self.real_email, roles=self.real_roles, mode=self.mode)


class TeamMember(BaseModel):
    """A person allowed into the workbench, as listed on the Team screen."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    email: str
    roles: list[str]
    added_by: str
    created_at: str
