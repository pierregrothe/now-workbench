# src/now_workbench/domains/groups/models.py
# Groups (region, territory, business unit) and their members (PRD-003).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Group models."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

__all__ = [
    "Group",
    "GroupKind",
    "GroupMember",
    "MemberRole",
    "MemberStatus",
]


class GroupKind(StrEnum):
    """How a group slices the organisation."""

    REGION = "region"
    TERRITORY = "territory"
    BUSINESS_UNIT = "business_unit"


class MemberRole(StrEnum):
    """A member's role inside one group."""

    MEMBER = "member"
    ADMIN = "admin"


class MemberStatus(StrEnum):
    """Whether a join request was accepted."""

    PENDING = "pending"
    ACTIVE = "active"


class Group(BaseModel):
    """A group, with the signed-in person's own standing in it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    name: str
    kind: GroupKind
    description: str = ""
    member_count: int = 0
    my_status: MemberStatus | None = None
    my_role: MemberRole | None = None


class GroupMember(BaseModel):
    """One person's membership of a group."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    group_id: str
    email: str
    role: MemberRole
    status: MemberStatus
    requested_at: str
