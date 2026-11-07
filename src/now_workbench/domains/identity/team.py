# src/now_workbench/domains/identity/team.py
# Who may use the workbench and with which roles; the rules shared by the API and Otto.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Team service (ADR-017, ADR-025): administrators add people, change roles and remove them."""

import re
import sqlite3

from now_workbench.domains.identity.models import AuthUser, Role, TeamMember
from now_workbench.domains.identity.repository import UserRepository
from now_workbench.platform.errors import (
    ConflictError,
    ForbiddenError,
    InvalidInputError,
    NotFoundError,
)

__all__ = [
    "is_admin",
    "list_team",
    "normalize_email",
    "remove_member",
    "require_admin",
    "set_roles",
]

_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}$")
_LAST_ADMIN = "The workbench needs at least one administrator."


def is_admin(user: AuthUser) -> bool:
    """Return True for a workbench administrator."""
    return Role.ADMIN in user.roles


def require_admin(user: AuthUser) -> None:
    """Refuse anyone but a workbench administrator.

    Raises:
        ForbiddenError: The person is not an administrator.
    """
    if not is_admin(user):
        raise ForbiddenError("Only administrators can do that.")


def normalize_email(raw: str) -> str:
    """Return the address lower-cased and trimmed.

    Raises:
        InvalidInputError: It is not an email address.
    """
    email = raw.strip().lower()
    if not _EMAIL.match(email):
        raise InvalidInputError("Enter a valid email address.")
    return email


def list_team(conn: sqlite3.Connection, actor: AuthUser) -> list[TeamMember]:
    """List everyone allowed in, with their roles (administrators)."""
    require_admin(actor)
    return UserRepository(conn).list_users()


def set_roles(
    conn: sqlite3.Connection, actor: AuthUser, email: str, admin: bool, consultant: bool
) -> list[TeamMember]:
    """Add a person or change their roles; at least one role, and one administrator remains.

    Raises:
        ForbiddenError: The actor is not an administrator.
        InvalidInputError: Bad address, or no role given.
        ConflictError: This would remove the last administrator.
    """
    require_admin(actor)
    address = normalize_email(email)
    roles = frozenset(
        r for r, on in ((Role.ADMIN, admin), (Role.SOLUTION_CONSULTANT, consultant)) if on
    )
    if not roles:
        raise InvalidInputError("Give at least one role, or remove the person.")
    users = UserRepository(conn)
    if Role.ADMIN in users.get_user_roles(address) and Role.ADMIN not in roles:
        if users.count_admins() == 1:
            raise ConflictError(_LAST_ADMIN)
    users.put_user(address, roles, added_by=actor.email)
    return users.list_users()


def remove_member(conn: sqlite3.Connection, actor: AuthUser, email: str) -> list[TeamMember]:
    """Remove a person's access; the last administrator stays.

    Raises:
        ForbiddenError: The actor is not an administrator.
        NotFoundError: No such member.
        ConflictError: This is the last administrator.
    """
    require_admin(actor)
    address = normalize_email(email)
    users = UserRepository(conn)
    current = users.get_user_roles(address)
    if not current:
        raise NotFoundError("No such member.")
    if Role.ADMIN in current and users.count_admins() == 1:
        raise ConflictError(_LAST_ADMIN)
    users.delete_user(address)
    return users.list_users()
