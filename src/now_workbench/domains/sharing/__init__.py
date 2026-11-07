# src/now_workbench/domains/sharing/__init__.py
# Public root of the sharing domain: other packages import only what is listed here.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Sharing package; import submodules directly (access depends on the repository)."""

from now_workbench.domains.sharing.access import (
    BundleAccess,
    ReadOnlyBundleError,
    list_accessible,
    register_new_bundle,
    resolve_bundle,
    save_version,
    sync_registry,
)
from now_workbench.domains.sharing.models import (
    ArtifactShare,
    ArtifactVersion,
    ShareStatus,
    ShareTarget,
)
from now_workbench.domains.sharing.repository import ArtifactRepository
from now_workbench.domains.sharing.service import (
    ApprovalInbox,
    approval_inbox,
    create_group,
    decide_share,
    delete_group,
    join_group,
    list_group_members,
    list_groups,
    list_shares,
    list_versions,
    put_group_member,
    remove_group_member,
    request_share,
    save_new_version,
    withdraw_share,
)
from now_workbench.domains.sharing.store import delete_artifact_files

__all__ = [
    "approval_inbox",
    "ApprovalInbox",
    "ArtifactRepository",
    "ArtifactShare",
    "ArtifactVersion",
    "BundleAccess",
    "create_group",
    "decide_share",
    "delete_artifact_files",
    "delete_group",
    "join_group",
    "list_accessible",
    "list_group_members",
    "list_groups",
    "list_shares",
    "list_versions",
    "put_group_member",
    "ReadOnlyBundleError",
    "register_new_bundle",
    "remove_group_member",
    "request_share",
    "resolve_bundle",
    "save_new_version",
    "save_version",
    "ShareStatus",
    "ShareTarget",
    "sync_registry",
    "withdraw_share",
]
