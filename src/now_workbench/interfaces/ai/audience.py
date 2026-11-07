# src/now_workbench/interfaces/ai/audience.py
# Who Otto is helping: identity, roles, groups and rights, told to Claude on every request.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Audience of a conversation (ADR-026).

The description goes in a second system block after the cached prefix (ADR-023). It only
changes when the person's roles or groups change, so a conversation keeps hitting the cache.
"""

import sqlite3
from dataclasses import dataclass

from now_workbench.domains.groups import GroupRepository, MemberRole, MemberStatus
from now_workbench.domains.identity import AuthUser, Role, is_admin
from now_workbench.domains.profile import ProfileRepository

__all__ = ["Audience", "audience_for"]

_ROLE_NAMES = {Role.ADMIN: "Administrator", Role.SOLUTION_CONSULTANT: "Solution Consultant"}

_ADMIN_RIGHTS = (
    "As an administrator they may manage the team and its roles, the conversation limits and "
    "every group, and approve any share, including shares with everyone."
)
_MEMBER_RIGHTS = (
    "They work with their own instances and demo bundles, see what was shared with them, ask "
    "to join groups and share their bundles with their groups (a group administrator or an "
    "administrator approves). They may not manage the team, the limits or create groups; if "
    "they ask, explain who can and offer what they can do instead."
)


@dataclass(frozen=True)
class Audience:
    """The person Otto helps, as far as Claude needs to know.

    Attributes:
        description: Text for the second system block ("" when nobody is signed in).
        admin: Offer administrator tools.
    """

    description: str = ""
    admin: bool = True


def _groups_line(conn: sqlite3.Connection, user: AuthUser) -> str:
    groups = GroupRepository(conn).list_groups(user.email)
    led = [
        g.name
        for g in groups
        if g.my_role is MemberRole.ADMIN and g.my_status is MemberStatus.ACTIVE
    ]
    member = [
        g.name
        for g in groups
        if g.my_status is MemberStatus.ACTIVE and g.my_role is not MemberRole.ADMIN
    ]
    pending = [g.name for g in groups if g.my_status is MemberStatus.PENDING]
    parts = []
    if led:
        parts.append(f"administers {', '.join(led)} (accepts join requests, approves shares there)")
    if member:
        parts.append(f"member of {', '.join(member)}")
    if pending:
        parts.append(f"asked to join {', '.join(pending)}")
    return "; ".join(parts) or "not in any group yet"


def audience_for(conn: sqlite3.Connection, user: AuthUser | None) -> Audience:
    """Describe ``user`` for Otto; an unknown person gets no description and every tool."""
    if user is None:
        return Audience()
    name = ProfileRepository(conn).get_profile(user.email).display_name or user.email
    roles = ", ".join(_ROLE_NAMES[r] for r in sorted(user.roles)) or "no role"
    admin = is_admin(user)
    lines = [
        "The person you are helping:",
        f"- {name} <{user.email}>",
        f"- Roles: {roles}",
        f"- Groups: {_groups_line(conn, user)}",
        f"- {_ADMIN_RIGHTS if admin else _MEMBER_RIGHTS}",
    ]
    if user.real_email:
        lines.append(
            f"- An administrator ({user.real_email}) is viewing the workbench as this person: act "
            "strictly with this person's rights, and say so if asked who you are working for."
        )
    lines.append("Address them by first name when it fits; never list these facts back unasked.")
    return Audience(description="\n".join(lines), admin=admin)
