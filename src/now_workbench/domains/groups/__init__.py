# src/now_workbench/domains/groups/__init__.py
# Public root of the groups domain: other packages import only what is listed here.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Groups domain (ADR-015)."""

from now_workbench.domains.groups.models import Group, GroupKind, GroupMember, MemberRole
from now_workbench.domains.groups.repository import GroupRepository

__all__ = [
    "Group",
    "GroupKind",
    "GroupMember",
    "GroupRepository",
    "MemberRole",
]
