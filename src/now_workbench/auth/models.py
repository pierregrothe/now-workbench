# src/now_workbench/auth/models.py
# Roles and the authenticated user.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Role and user models."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict

__all__ = ["LOCAL_EMAIL", "AuthUser", "Role"]

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
