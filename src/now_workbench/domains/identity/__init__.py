# src/now_workbench/domains/identity/__init__.py
# Public root of the identity domain: other packages import only what is listed here.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Identity domain (ADR-015)."""

from now_workbench.domains.identity.actor import NoActorError, actor_scope, current_actor
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
from now_workbench.domains.identity.team import (
    is_admin,
    list_team,
    normalize_email,
    remove_member,
    require_admin,
    set_roles,
)

__all__ = [
    "actor_scope",
    "AuthUser",
    "candidates",
    "current_actor",
    "effective_user",
    "is_admin",
    "list_team",
    "may_impersonate",
    "NoActorError",
    "normalize_email",
    "operator_owner",
    "remove_member",
    "require_admin",
    "Role",
    "set_roles",
    "SetupCodes",
    "SetupError",
    "TeamMember",
    "TooManyAttemptsError",
    "UserRepository",
    "WrongCodeError",
]
