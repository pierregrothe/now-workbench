# src/now_workbench/api/sharing.py
# Groups, artifact versions and shares, and the approvals inbox (PRD-003, ADR-018).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Sharing API.

Who may do what:

* Administrators create and delete groups, appoint group administrators, and approve shares
  with everyone (and any group's shares).
* Group administrators accept join requests and approve shares with their group.
* An artifact's owner saves versions and asks to share them; approvers sharing to a target they
  approve are approved at once.
"""

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from now_workbench.auth.guard import current_user, require_role
from now_workbench.auth.models import AuthUser, Role
from now_workbench.db import db_session
from now_workbench.db.repository import DatabaseRepository
from now_workbench.sharing.access import save_version
from now_workbench.sharing.models import (
    ArtifactShare,
    ArtifactVersion,
    Group,
    GroupKind,
    GroupMember,
    MemberRole,
    ShareStatus,
    ShareTarget,
)

__all__ = ["approvals_router", "artifacts_router", "groups_router"]

groups_router = APIRouter(prefix="/api/groups", tags=["groups"])
artifacts_router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])
approvals_router = APIRouter(prefix="/api/approvals", tags=["approvals"])

_admin = require_role(Role.ADMIN)
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}$")


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


class ApprovalInbox(BaseModel):
    """Everything waiting for the signed-in approver."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    shares: list[ArtifactShare]
    join_requests: list[GroupMember]
    group_names: dict[str, str]


def _is_admin(user: AuthUser) -> bool:
    return Role.ADMIN in user.roles


def _require_group(repo: DatabaseRepository, group_id: str, viewer: str) -> Group:
    group = repo.get_group(group_id, viewer)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found.")
    return group


def _require_group_admin(repo: DatabaseRepository, group_id: str, user: AuthUser) -> Group:
    group = _require_group(repo, group_id, user.email)
    if not (_is_admin(user) or repo.is_group_admin(group_id, user.email)):
        raise HTTPException(status_code=403, detail="Only this group's administrators can do that.")
    return group


def _require_owner(repo: DatabaseRepository, artifact_id: str, user: AuthUser) -> None:
    if repo.artifact_owner(artifact_id) != user.email:
        raise HTTPException(status_code=404, detail="Demo bundle not found.")


# --- groups ------------------------------------------------------------------------------


@groups_router.get("", response_model=list[Group])
def list_groups(user: AuthUser = Depends(current_user)) -> list[Group]:
    """List every group with the signed-in person's standing in it."""
    with db_session() as repo:
        return repo.list_groups(user.email)


@groups_router.post("", response_model=Group)
def create_group(req: GroupCreate, user: AuthUser = Depends(_admin)) -> Group:
    """Create a group (administrators)."""
    with db_session() as repo:
        try:
            return repo.create_group(
                req.name.strip(), req.kind, req.description.strip(), user.email
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc


@groups_router.delete("/{group_id}")
def delete_group(group_id: str, _user: AuthUser = Depends(_admin)) -> dict[str, bool]:
    """Delete a group; its memberships and shares go with it (administrators)."""
    with db_session() as repo:
        if not repo.delete_group(group_id):
            raise HTTPException(status_code=404, detail="Group not found.")
    return {"deleted": True}


@groups_router.post("/{group_id}/join", response_model=Group)
def join_group(group_id: str, user: AuthUser = Depends(current_user)) -> Group:
    """Ask to join a group; a group administrator decides."""
    with db_session() as repo:
        _require_group(repo, group_id, user.email)
        repo.request_to_join(group_id, user.email)
        return _require_group(repo, group_id, user.email)


@groups_router.get("/{group_id}/members", response_model=list[GroupMember])
def list_members(group_id: str, user: AuthUser = Depends(current_user)) -> list[GroupMember]:
    """List members and pending requests (group administrators)."""
    with db_session() as repo:
        _require_group_admin(repo, group_id, user)
        return repo.list_group_members(group_id)


@groups_router.put("/{group_id}/members/{email}", response_model=list[GroupMember])
def put_member(
    group_id: str, email: str, req: MemberUpdate, user: AuthUser = Depends(current_user)
) -> list[GroupMember]:
    """Accept a request or add a workbench member; only administrators appoint group admins."""
    target = email.strip().lower()
    if not _EMAIL.match(target):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if req.role is MemberRole.ADMIN and not _is_admin(user):
        raise HTTPException(
            status_code=403, detail="Only administrators appoint group administrators."
        )
    with db_session() as repo:
        _require_group_admin(repo, group_id, user)
        if not repo.get_user_roles(target):
            raise HTTPException(status_code=422, detail=f"{target} is not on the Team yet.")
        repo.put_group_member(group_id, target, req.role, decided_by=user.email)
        return repo.list_group_members(group_id)


@groups_router.delete("/{group_id}/members/{email}")
def remove_member(
    group_id: str, email: str, user: AuthUser = Depends(current_user)
) -> dict[str, bool]:
    """Leave a group, decline a request, or remove a member."""
    target = email.strip().lower()
    with db_session() as repo:
        if target != user.email:
            _require_group_admin(repo, group_id, user)
        if not repo.remove_group_member(group_id, target):
            raise HTTPException(status_code=404, detail="Not a member of this group.")
    return {"removed": True}


# --- artifacts: versions and shares --------------------------------------------------------


@artifacts_router.get("/{artifact_id}/versions", response_model=list[ArtifactVersion])
def list_versions(
    artifact_id: str, user: AuthUser = Depends(current_user)
) -> list[ArtifactVersion]:
    """List an artifact's versions, newest first (owner)."""
    with db_session() as repo:
        _require_owner(repo, artifact_id, user)
        return repo.list_artifact_versions(artifact_id)


@artifacts_router.post("/{artifact_id}/versions", response_model=ArtifactVersion)
def create_version(
    artifact_id: str, req: VersionCreate, user: AuthUser = Depends(current_user)
) -> ArtifactVersion:
    """Freeze the artifact as its next version (owner)."""
    with db_session() as repo:
        _require_owner(repo, artifact_id, user)
        return save_version(repo, artifact_id, req.note.strip(), created_by=user.email)


@artifacts_router.get("/{artifact_id}/shares", response_model=list[ArtifactShare])
def list_shares(artifact_id: str, user: AuthUser = Depends(current_user)) -> list[ArtifactShare]:
    """List pending and approved shares of an artifact (owner)."""
    with db_session() as repo:
        _require_owner(repo, artifact_id, user)
        return repo.list_artifact_shares(artifact_id)


@artifacts_router.post("/{artifact_id}/shares", response_model=ArtifactShare)
def create_share(
    artifact_id: str, req: ShareCreate, user: AuthUser = Depends(current_user)
) -> ArtifactShare:
    """Ask to share the newest version with a group (you must belong) or everyone."""
    with db_session() as repo:
        _require_owner(repo, artifact_id, user)
        versions = repo.list_artifact_versions(artifact_id)
        if not versions:
            raise HTTPException(status_code=409, detail="Save a version before sharing.")
        approver = _is_admin(user)
        group_id: str | None = None
        if req.target is ShareTarget.GROUP:
            if not req.group_id:
                raise HTTPException(status_code=422, detail="Choose a group.")
            _require_group(repo, req.group_id, user.email)
            if req.group_id not in repo.active_group_ids(user.email) and not approver:
                raise HTTPException(status_code=403, detail="You can only share with your groups.")
            group_id = req.group_id
            approver = approver or repo.is_group_admin(group_id, user.email)
        share = repo.request_share(
            artifact_id, versions[0].version, req.target, group_id, requested_by=user.email
        )
        if approver:
            share = repo.decide_share(share.id, approve=True, decided_by=user.email)
        return share


@artifacts_router.delete("/{artifact_id}/shares/{share_id}")
def withdraw_share(
    artifact_id: str, share_id: str, user: AuthUser = Depends(current_user)
) -> dict[str, bool]:
    """Stop sharing, or withdraw a request (owner)."""
    with db_session() as repo:
        _require_owner(repo, artifact_id, user)
        share = repo.get_share(share_id)
        if share is None or share.artifact_id != artifact_id:
            raise HTTPException(status_code=404, detail="Share not found.")
        repo.withdraw_share(share_id)
    return {"withdrawn": True}


# --- approvals -----------------------------------------------------------------------------


@approvals_router.get("", response_model=ApprovalInbox)
def approval_inbox(user: AuthUser = Depends(current_user)) -> ApprovalInbox:
    """Return the shares and join requests the signed-in person may decide."""
    with db_session() as repo:
        admin = _is_admin(user)
        groups = repo.list_groups(user.email)
        scope = [g.id for g in groups] if admin else repo.administered_group_ids(user.email)
        return ApprovalInbox(
            shares=repo.pending_shares(scope, include_global=admin),
            join_requests=repo.pending_join_requests(None if admin else scope),
            group_names={g.id: g.name for g in groups},
        )


@approvals_router.post("/shares/{share_id}", response_model=ArtifactShare)
def decide_share(
    share_id: str, req: Decision, user: AuthUser = Depends(current_user)
) -> ArtifactShare:
    """Approve or reject a pending share you are allowed to decide."""
    with db_session() as repo:
        share = repo.get_share(share_id)
        if share is None or share.status is not ShareStatus.PENDING:
            raise HTTPException(status_code=404, detail="Nothing to decide here.")
        allowed = _is_admin(user) or (
            share.target is ShareTarget.GROUP
            and share.group_id is not None
            and repo.is_group_admin(share.group_id, user.email)
        )
        if not allowed:
            raise HTTPException(status_code=403, detail="You cannot decide this share.")
        return repo.decide_share(share_id, approve=req.approve, decided_by=user.email)
