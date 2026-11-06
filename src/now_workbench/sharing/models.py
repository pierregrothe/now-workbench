# src/now_workbench/sharing/models.py
# Groups, artifact versions and shares (PRD-003, ADR-018).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Sharing models."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "AccessKind",
    "ArtifactShare",
    "ArtifactVersion",
    "Group",
    "GroupKind",
    "GroupMember",
    "MemberRole",
    "MemberStatus",
    "ShareStatus",
    "ShareTarget",
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


class ShareTarget(StrEnum):
    """Who a share is for."""

    GROUP = "group"
    GLOBAL = "global"


class ShareStatus(StrEnum):
    """Where a share stands."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class AccessKind(StrEnum):
    """How the signed-in person reaches an artifact."""

    OWNER = "owner"
    SHARED = "shared"


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


class ArtifactVersion(BaseModel):
    """An immutable snapshot of an artifact."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_id: str
    version: int = Field(ge=1)
    name: str
    description: str = ""
    note: str = ""
    size_bytes: int = 0
    created_by: str
    created_at: str


class ArtifactShare(BaseModel):
    """A request to show one version of an artifact to a group or to everyone."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    artifact_id: str
    artifact_name: str = ""
    version: int
    target: ShareTarget
    group_id: str | None = None
    group_name: str | None = None
    status: ShareStatus
    requested_by: str
    requested_at: str
    decided_by: str | None = None
    decided_at: str | None = None
