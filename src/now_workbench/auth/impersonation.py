# src/now_workbench/auth/impersonation.py
# Who may act as whom, and the effective user of a request (ADR-020).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Impersonation rules.

* An administrator may act as any member of the workbench.
* A group administrator may act as accepted members of a group they administer, but never as a
  workbench administrator (that would hand them powers they do not have).
* Nobody acts as themselves, as someone without a role, or starts from inside an impersonation:
  rights are always those of the person really signed in, and they are re-checked on every
  request, so removing a group admin's role ends their impersonation at once.
"""

import logging
import sqlite3

from now_workbench.auth.models import AuthUser, Role
from now_workbench.db.repos.groups import GroupRepository
from now_workbench.db.repos.users import UserRepository

__all__ = ["candidates", "effective_user", "may_impersonate"]

_log = logging.getLogger("uvicorn.error")


def may_impersonate(conn: sqlite3.Connection, real: AuthUser, target: str) -> bool:
    """Return True when ``real`` (the signed-in person) may act as ``target``."""
    group_repo = GroupRepository(conn)
    if target == real.email:
        return False
    target_roles = UserRepository(conn).get_user_roles(target)
    if not target_roles:
        return False
    if Role.ADMIN in real.roles:
        return True
    if Role.ADMIN in target_roles:
        return False
    targets_groups = set(group_repo.active_group_ids(target))
    return any(g in targets_groups for g in group_repo.administered_group_ids(real.email))


def candidates(conn: sqlite3.Connection, real: AuthUser) -> list[str]:
    """Return everyone ``real`` may act as, sorted."""
    return sorted(
        m.email for m in UserRepository(conn).list_users() if may_impersonate(conn, real, m.email)
    )


def effective_user(conn: sqlite3.Connection, real: AuthUser) -> AuthUser:
    """Return who a request acts as: the impersonated person, or ``real`` itself.

    An impersonation that is no longer allowed is ended (logged as revoked).
    """
    user_repo = UserRepository(conn)
    target = user_repo.get_impersonation(real.email)
    if target is None:
        return real
    if not may_impersonate(conn, real, target):
        user_repo.end_impersonation(real.email, action="revoked")
        _log.warning("Impersonation of %s by %s revoked: no longer allowed.", target, real.email)
        return real
    return AuthUser(
        email=target,
        roles=user_repo.get_user_roles(target),
        mode=real.mode,
        real_email=real.email,
        real_roles=real.roles,
    )
