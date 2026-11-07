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
from now_workbench.domains.sharing.store import delete_artifact_files

__all__ = [
    "ArtifactRepository",
    "ArtifactShare",
    "ArtifactVersion",
    "BundleAccess",
    "delete_artifact_files",
    "list_accessible",
    "ReadOnlyBundleError",
    "register_new_bundle",
    "resolve_bundle",
    "save_version",
    "ShareStatus",
    "ShareTarget",
    "sync_registry",
]
