# src/now_workbench/interfaces/api/team.py
# Admin-only management of who may use the workbench and with which roles.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Team API (ADR-017). There is always at least one administrator."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from now_workbench.domains import identity
from now_workbench.domains.identity import AuthUser, Role, TeamMember
from now_workbench.interfaces.api.guard import require_role
from now_workbench.platform.db.session import db_session

__all__ = ["router"]

router = APIRouter(prefix="/api/team", tags=["team"])
# Refuse non-administrators before reading the body; the service checks again (ADR-025).
_user = Depends(require_role(Role.ADMIN))


class MemberRoles(BaseModel):
    """Roles to give a member."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    admin: bool = False
    solution_consultant: bool = False


@router.get("", response_model=list[TeamMember])
def list_members(user: AuthUser = _user) -> list[TeamMember]:
    """List everyone allowed in, with their roles (administrators)."""
    with db_session() as conn:
        return identity.list_team(conn, user)


@router.put("/{email}", response_model=list[TeamMember])
def put_member(email: str, req: MemberRoles, user: AuthUser = _user) -> list[TeamMember]:
    """Add a person or change their roles (at least one role; use DELETE to remove)."""
    with db_session() as conn:
        return identity.set_roles(conn, user, email, req.admin, req.solution_consultant)


@router.delete("/{email}", response_model=list[TeamMember])
def remove_member(email: str, user: AuthUser = _user) -> list[TeamMember]:
    """Remove a person's access (administrators)."""
    with db_session() as conn:
        return identity.remove_member(conn, user, email)
