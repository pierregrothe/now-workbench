# src/now_workbench/domains/sharing/service.py
# Groups, membership, versions, shares and approvals: the rules the API and Otto both apply.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Sharing service (PRD-003, ADR-018, ADR-025).

Who may do what:

* Administrators create and delete groups, appoint group administrators, and approve shares
  with everyone (and any group's shares).
* Group administrators accept join requests and approve shares with their group.
* An artifact's owner saves versions and asks to share them; approvers sharing to a target they
  approve are approved at once.
"""

import sqlite3

from pydantic import BaseModel, ConfigDict

from now_workbench.domains.groups import Group, GroupKind, GroupMember, GroupRepository, MemberRole
from now_workbench.domains.identity import (
    AuthUser,
    UserRepository,
    is_admin,
    normalize_email,
    require_admin,
)
from now_workbench.domains.sharing.access import save_version
from now_workbench.domains.sharing.models import (
    ArtifactShare,
    ArtifactVersion,
    ShareStatus,
    ShareTarget,
)
from now_workbench.domains.sharing.repository import ArtifactRepository
from now_workbench.platform.errors import (
    ConflictError,
    ForbiddenError,
    InvalidInputError,
    NotFoundError,
)

__all__ = [
    "ApprovalInbox",
    "approval_inbox",
    "create_group",
    "decide_share",
    "delete_group",
    "join_group",
    "list_group_members",
    "list_groups",
    "list_shares",
    "list_versions",
    "put_group_member",
    "remove_group_member",
    "request_share",
    "save_new_version",
    "withdraw_share",
]


class ApprovalInbox(BaseModel):
    """Everything waiting for the signed-in approver."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    shares: list[ArtifactShare]
    join_requests: list[GroupMember]
    group_names: dict[str, str]


def _group(conn: sqlite3.Connection, group_id: str, viewer: str) -> Group:
    group = GroupRepository(conn).get_group(group_id, viewer)
    if group is None:
        raise NotFoundError("Group not found.")
    return group


def _require_group_admin(conn: sqlite3.Connection, group_id: str, actor: AuthUser) -> Group:
    group = _group(conn, group_id, actor.email)
    if not (is_admin(actor) or GroupRepository(conn).is_group_admin(group_id, actor.email)):
        raise ForbiddenError("Only this group's administrators can do that.")
    return group


def _require_owner(conn: sqlite3.Connection, artifact_id: str, actor: AuthUser) -> None:
    # A bundle you do not own is reported as missing, so its existence does not leak.
    if ArtifactRepository(conn).artifact_owner(artifact_id) != actor.email:
        raise NotFoundError("Demo bundle not found.")


# --- groups ------------------------------------------------------------------------------


def list_groups(conn: sqlite3.Connection, actor: AuthUser) -> list[Group]:
    """Every group, with the actor's standing in it."""
    return GroupRepository(conn).list_groups(actor.email)


def create_group(
    conn: sqlite3.Connection, actor: AuthUser, name: str, kind: GroupKind, description: str
) -> Group:
    """Create a group (administrators).

    Raises:
        ForbiddenError: Not an administrator.
        ConflictError: A group with that name exists.
    """
    require_admin(actor)
    try:
        return GroupRepository(conn).create_group(
            name.strip(), kind, description.strip(), actor.email
        )
    except ValueError as exc:
        raise ConflictError(str(exc)) from exc


def delete_group(conn: sqlite3.Connection, actor: AuthUser, group_id: str) -> None:
    """Delete a group with its memberships and shares (administrators)."""
    require_admin(actor)
    if not GroupRepository(conn).delete_group(group_id):
        raise NotFoundError("Group not found.")


def join_group(conn: sqlite3.Connection, actor: AuthUser, group_id: str) -> Group:
    """Ask to join a group; a group administrator decides."""
    _group(conn, group_id, actor.email)
    GroupRepository(conn).request_to_join(group_id, actor.email)
    return _group(conn, group_id, actor.email)


def list_group_members(
    conn: sqlite3.Connection, actor: AuthUser, group_id: str
) -> list[GroupMember]:
    """Members and pending requests (group administrators)."""
    _require_group_admin(conn, group_id, actor)
    return GroupRepository(conn).list_group_members(group_id)


def put_group_member(
    conn: sqlite3.Connection, actor: AuthUser, group_id: str, email: str, role: MemberRole
) -> list[GroupMember]:
    """Accept a request or add a team member; only administrators appoint group admins.

    Raises:
        InvalidInputError: Bad address, or the person is not on the team.
        ForbiddenError: Not allowed to manage this group or to appoint an admin.
    """
    target = normalize_email(email)
    if role is MemberRole.ADMIN and not is_admin(actor):
        raise ForbiddenError("Only administrators appoint group administrators.")
    _require_group_admin(conn, group_id, actor)
    if not UserRepository(conn).get_user_roles(target):
        raise InvalidInputError(f"{target} is not on the Team yet.")
    groups = GroupRepository(conn)
    groups.put_group_member(group_id, target, role, decided_by=actor.email)
    return groups.list_group_members(group_id)


def remove_group_member(
    conn: sqlite3.Connection, actor: AuthUser, group_id: str, email: str
) -> None:
    """Leave a group, decline a request, or remove a member."""
    target = email.strip().lower()
    if target != actor.email:
        _require_group_admin(conn, group_id, actor)
    if not GroupRepository(conn).remove_group_member(group_id, target):
        raise NotFoundError("Not a member of this group.")


# --- versions and shares -------------------------------------------------------------------


def list_versions(
    conn: sqlite3.Connection, actor: AuthUser, artifact_id: str
) -> list[ArtifactVersion]:
    """An artifact's versions, newest first (owner)."""
    _require_owner(conn, artifact_id, actor)
    return ArtifactRepository(conn).list_artifact_versions(artifact_id)


def save_new_version(
    conn: sqlite3.Connection, actor: AuthUser, artifact_id: str, note: str
) -> ArtifactVersion:
    """Freeze the artifact as its next version (owner)."""
    _require_owner(conn, artifact_id, actor)
    return save_version(conn, artifact_id, note.strip(), created_by=actor.email)


def list_shares(conn: sqlite3.Connection, actor: AuthUser, artifact_id: str) -> list[ArtifactShare]:
    """Pending and approved shares of an artifact (owner)."""
    _require_owner(conn, artifact_id, actor)
    return ArtifactRepository(conn).list_artifact_shares(artifact_id)


def request_share(
    conn: sqlite3.Connection,
    actor: AuthUser,
    artifact_id: str,
    target: ShareTarget,
    group_id: str | None = None,
) -> ArtifactShare:
    """Share the newest version with a group (the actor's) or everyone; approvers skip the queue.

    Raises:
        NotFoundError: Not the owner, or no such group.
        ConflictError: No version saved yet.
        InvalidInputError: A group share without a group.
        ForbiddenError: Sharing with a group the actor does not belong to.
    """
    _require_owner(conn, artifact_id, actor)
    artifacts = ArtifactRepository(conn)
    versions = artifacts.list_artifact_versions(artifact_id)
    if not versions:
        raise ConflictError("Save a version before sharing.")
    approver = is_admin(actor)
    if target is ShareTarget.GROUP:
        if not group_id:
            raise InvalidInputError("Choose a group.")
        _group(conn, group_id, actor.email)
        groups = GroupRepository(conn)
        if group_id not in groups.active_group_ids(actor.email) and not approver:
            raise ForbiddenError("You can only share with your groups.")
        approver = approver or groups.is_group_admin(group_id, actor.email)
    else:
        group_id = None
    share = artifacts.request_share(
        artifact_id, versions[0].version, target, group_id, requested_by=actor.email
    )
    if approver:
        share = artifacts.decide_share(share.id, approve=True, decided_by=actor.email)
    return share


def withdraw_share(
    conn: sqlite3.Connection, actor: AuthUser, artifact_id: str, share_id: str
) -> None:
    """Stop sharing, or withdraw a request (owner)."""
    _require_owner(conn, artifact_id, actor)
    artifacts = ArtifactRepository(conn)
    share = artifacts.get_share(share_id)
    if share is None or share.artifact_id != artifact_id:
        raise NotFoundError("Share not found.")
    artifacts.withdraw_share(share_id)


# --- approvals -----------------------------------------------------------------------------


def approval_inbox(conn: sqlite3.Connection, actor: AuthUser) -> ApprovalInbox:
    """The shares and join requests the actor may decide."""
    groups = GroupRepository(conn)
    admin = is_admin(actor)
    listed = groups.list_groups(actor.email)
    scope = [g.id for g in listed] if admin else groups.administered_group_ids(actor.email)
    return ApprovalInbox(
        shares=ArtifactRepository(conn).pending_shares(scope, include_global=admin),
        join_requests=groups.pending_join_requests(None if admin else scope),
        group_names={g.id: g.name for g in listed},
    )


def decide_share(
    conn: sqlite3.Connection, actor: AuthUser, share_id: str, approve: bool
) -> ArtifactShare:
    """Approve or reject a pending share the actor is allowed to decide."""
    artifacts = ArtifactRepository(conn)
    share = artifacts.get_share(share_id)
    if share is None or share.status is not ShareStatus.PENDING:
        raise NotFoundError("Nothing to decide here.")
    allowed = is_admin(actor) or (
        share.target is ShareTarget.GROUP
        and share.group_id is not None
        and GroupRepository(conn).is_group_admin(share.group_id, actor.email)
    )
    if not allowed:
        raise ForbiddenError("You cannot decide this share.")
    return artifacts.decide_share(share_id, approve=approve, decided_by=actor.email)
