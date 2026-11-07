# src/now_workbench/domains/identity/__init__.py
# Public root of the identity domain: other packages import only what is listed here.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Identity domain (ADR-015)."""

from now_workbench.domains.identity.impersonation import (
    candidates,
    effective_user,
    may_impersonate,
)
from now_workbench.domains.identity.models import AuthUser, Role, TeamMember
from now_workbench.domains.identity.owner import operator_owner
from now_workbench.domains.identity.repository import UserRepository
from now_workbench.domains.identity.setup import (
    SetupCodes,
    SetupError,
    TooManyAttemptsError,
    WrongCodeError,
)

__all__ = [
    "AuthUser",
    "candidates",
    "effective_user",
    "may_impersonate",
    "operator_owner",
    "Role",
    "SetupCodes",
    "SetupError",
    "TeamMember",
    "TooManyAttemptsError",
    "UserRepository",
    "WrongCodeError",
]
