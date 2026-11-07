# src/now_workbench/interfaces/api/sharing.py
# Groups, artifact versions and shares, and the approvals inbox (PRD-003, ADR-018).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Sharing API: thin routes over the sharing service, which holds every rule (ADR-025)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from now_workbench.domains import sharing
from now_workbench.domains.groups import Group, GroupKind, GroupMember, MemberRole
from now_workbench.domains.identity import AuthUser, Role
from now_workbench.domains.sharing import (
    ApprovalInbox,
    ArtifactShare,
    ArtifactVersion,
    ShareTarget,
)
from now_workbench.interfaces.api.guard import current_user, require_role
from now_workbench.platform.db.session import db_session

__all__ = ["approvals_router", "artifacts_router", "groups_router"]

groups_router = APIRouter(prefix="/api/groups", tags=["groups"])
artifacts_router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])
approvals_router = APIRouter(prefix="/api/approvals", tags=["approvals"])


class GroupCreate(BaseModel):
    """A new group."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=2, max_length=80)
    kind: GroupKind
    description: str = Field(default="", max_length=400)


class MemberUpdate(BaseModel):
    """Accept a member (or add one directly) with a role."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    role: MemberRole = MemberRole.MEMBER


class VersionCreate(BaseModel):
    """What changed in this version."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    note: str = Field(default="", max_length=400)


class ShareCreate(BaseModel):
    """Share the newest version with a group or with everyone."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    target: ShareTarget
    group_id: str | None = None


class Decision(BaseModel):
    """An approver's decision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    approve: bool


_user = Depends(current_user)
# Admin-only routes refuse before reading the body; the service checks again (ADR-025).
_admin = Depends(require_role(Role.ADMIN))


# --- groups ------------------------------------------------------------------------------


@groups_router.get("", response_model=list[Group])
def list_groups(user: AuthUser = _user) -> list[Group]:
    """List every group with the signed-in person's standing in it."""
    with db_session() as conn:
        return sharing.list_groups(conn, user)


@groups_router.post("", response_model=Group)
def create_group(req: GroupCreate, user: AuthUser = _admin) -> Group:
    """Create a group (administrators)."""
    with db_session() as conn:
        return sharing.create_group(conn, user, req.name, req.kind, req.description)


@groups_router.delete("/{group_id}")
def delete_group(group_id: str, user: AuthUser = _admin) -> dict[str, bool]:
    """Delete a group; its memberships and shares go with it (administrators)."""
    with db_session() as conn:
        sharing.delete_group(conn, user, group_id)
    return {"deleted": True}


@groups_router.post("/{group_id}/join", response_model=Group)
def join_group(group_id: str, user: AuthUser = _user) -> Group:
    """Ask to join a group; a group administrator decides."""
    with db_session() as conn:
        return sharing.join_group(conn, user, group_id)


@groups_router.get("/{group_id}/members", response_model=list[GroupMember])
def list_members(group_id: str, user: AuthUser = _user) -> list[GroupMember]:
    """List members and pending requests (group administrators)."""
    with db_session() as conn:
        return sharing.list_group_members(conn, user, group_id)


@groups_router.put("/{group_id}/members/{email}", response_model=list[GroupMember])
def put_member(
    group_id: str, email: str, req: MemberUpdate, user: AuthUser = _user
) -> list[GroupMember]:
    """Accept a request or add a workbench member; only administrators appoint group admins."""
    with db_session() as conn:
        return sharing.put_group_member(conn, user, group_id, email, req.role)


@groups_router.delete("/{group_id}/members/{email}")
def remove_member(group_id: str, email: str, user: AuthUser = _user) -> dict[str, bool]:
    """Leave a group, decline a request, or remove a member."""
    with db_session() as conn:
        sharing.remove_group_member(conn, user, group_id, email)
    return {"removed": True}


# --- artifacts: versions and shares --------------------------------------------------------


@artifacts_router.get("/{artifact_id}/versions", response_model=list[ArtifactVersion])
def list_versions(artifact_id: str, user: AuthUser = _user) -> list[ArtifactVersion]:
    """List an artifact's versions, newest first (owner)."""
    with db_session() as conn:
        return sharing.list_versions(conn, user, artifact_id)


@artifacts_router.post("/{artifact_id}/versions", response_model=ArtifactVersion)
def create_version(artifact_id: str, req: VersionCreate, user: AuthUser = _user) -> ArtifactVersion:
    """Freeze the artifact as its next version (owner)."""
    with db_session() as conn:
        return sharing.save_new_version(conn, user, artifact_id, req.note)


@artifacts_router.get("/{artifact_id}/shares", response_model=list[ArtifactShare])
def list_shares(artifact_id: str, user: AuthUser = _user) -> list[ArtifactShare]:
    """List pending and approved shares of an artifact (owner)."""
    with db_session() as conn:
        return sharing.list_shares(conn, user, artifact_id)


@artifacts_router.post("/{artifact_id}/shares", response_model=ArtifactShare)
def create_share(artifact_id: str, req: ShareCreate, user: AuthUser = _user) -> ArtifactShare:
    """Ask to share the newest version with a group (you must belong) or everyone."""
    with db_session() as conn:
        return sharing.request_share(conn, user, artifact_id, req.target, req.group_id)


@artifacts_router.delete("/{artifact_id}/shares/{share_id}")
def withdraw_share(artifact_id: str, share_id: str, user: AuthUser = _user) -> dict[str, bool]:
    """Stop sharing, or withdraw a request (owner)."""
    with db_session() as conn:
        sharing.withdraw_share(conn, user, artifact_id, share_id)
    return {"withdrawn": True}


# --- approvals -----------------------------------------------------------------------------


@approvals_router.get("", response_model=ApprovalInbox)
def approval_inbox(user: AuthUser = _user) -> ApprovalInbox:
    """Return the shares and join requests the signed-in person may decide."""
    with db_session() as conn:
        return sharing.approval_inbox(conn, user)


@approvals_router.post("/shares/{share_id}", response_model=ArtifactShare)
def decide_share(share_id: str, req: Decision, user: AuthUser = _user) -> ArtifactShare:
    """Approve or reject a pending share you are allowed to decide."""
    with db_session() as conn:
        return sharing.decide_share(conn, user, share_id, req.approve)
