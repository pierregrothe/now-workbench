# src/now_workbench/domains/releases/__init__.py
# Public root of the releases domain: other packages import only what is listed here.
# Author: Pierre Grothe
# Date: 2026-11-07
"""ServiceNow platform release hierarchy and workspace evolution services."""

from now_workbench.domains.releases.compatibility import (
    FEATURE_MINIMUM_RELEASES,
    compare_releases,
    evaluate_release_prerequisites,
    is_release_compatible,
    normalize_release,
)
from now_workbench.domains.releases.detection import BUILD_PROPERTY, parse_release_family
from now_workbench.domains.releases.models import (
    RELEASE_FAMILIES,
    UNKNOWN_RELEASE,
    ReleaseCompatibilityResult,
    WorkspaceRoute,
)
from now_workbench.domains.releases.workspaces import resolve_workspace, translate_workspace_url

__all__ = [
    "BUILD_PROPERTY",
    "compare_releases",
    "evaluate_release_prerequisites",
    "FEATURE_MINIMUM_RELEASES",
    "is_release_compatible",
    "normalize_release",
    "parse_release_family",
    "RELEASE_FAMILIES",
    "ReleaseCompatibilityResult",
    "resolve_workspace",
    "translate_workspace_url",
    "UNKNOWN_RELEASE",
    "WorkspaceRoute",
]
