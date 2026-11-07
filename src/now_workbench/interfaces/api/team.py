# src/now_workbench/interfaces/api/team.py
# Admin-only management of who may use the workbench and with which roles.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Team API (ADR-017). There is always at least one administrator."""

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from now_workbench.domains.identity import AuthUser, Role, TeamMember, UserRepository
from now_workbench.interfaces.api.guard import require_role
from now_workbench.platform.db.session import db_session

__all__ = ["router"]

router = APIRouter(prefix="/api/team", tags=["team"])
_admin = require_role(Role.ADMIN)
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}$")


class MemberRoles(BaseModel):
    """Roles to give a member."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    admin: bool = False
    solution_consultant: bool = False


def _email(raw: str) -> str:
    email = raw.strip().lower()
    if not _EMAIL.match(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    return email


@router.get("", response_model=list[TeamMember])
def list_members(_user: AuthUser = Depends(_admin)) -> list[TeamMember]:
    """List everyone allowed in, with their roles."""
    with db_session() as conn:
        return UserRepository(conn).list_users()


@router.put("/{email}", response_model=list[TeamMember])
def put_member(email: str, req: MemberRoles, user: AuthUser = Depends(_admin)) -> list[TeamMember]:
    """Add a person or change their roles (at least one role; use DELETE to remove)."""
    address = _email(email)
    roles = frozenset(
        r
        for r, on in ((Role.ADMIN, req.admin), (Role.SOLUTION_CONSULTANT, req.solution_consultant))
        if on
    )
    if not roles:
        raise HTTPException(status_code=422, detail="Give at least one role, or remove the person.")
    with db_session() as conn:
        user_repo = UserRepository(conn)
        current = user_repo.get_user_roles(address)
        if Role.ADMIN in current and Role.ADMIN not in roles and user_repo.count_admins() == 1:
            raise HTTPException(
                status_code=409, detail="The workbench needs at least one administrator."
            )
        user_repo.put_user(address, roles, added_by=user.email)
        return user_repo.list_users()


@router.delete("/{email}", response_model=list[TeamMember])
def remove_member(email: str, _user: AuthUser = Depends(_admin)) -> list[TeamMember]:
    """Remove a person's access."""
    address = _email(email)
    with db_session() as conn:
        user_repo = UserRepository(conn)
        current = user_repo.get_user_roles(address)
        if not current:
            raise HTTPException(status_code=404, detail="No such member.")
        if Role.ADMIN in current and user_repo.count_admins() == 1:
            raise HTTPException(
                status_code=409, detail="The workbench needs at least one administrator."
            )
        user_repo.delete_user(address)
        return user_repo.list_users()
