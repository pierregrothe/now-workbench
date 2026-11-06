"""ServiceNow platform release hierarchy and workspace evolution services."""

from now_workbench.releases.compatibility import (
    FEATURE_MINIMUM_RELEASES,
    compare_releases,
    evaluate_release_prerequisites,
    is_release_compatible,
    normalize_release,
)
from now_workbench.releases.detection import BUILD_PROPERTY, parse_release_family
from now_workbench.releases.models import (
    RELEASE_FAMILIES,
    ReleaseCompatibilityResult,
    WorkspaceRoute,
)
from now_workbench.releases.workspaces import (
    resolve_workspace,
    translate_workspace_url,
)

__all__ = [
    "BUILD_PROPERTY",
    "FEATURE_MINIMUM_RELEASES",
    "RELEASE_FAMILIES",
    "ReleaseCompatibilityResult",
    "WorkspaceRoute",
    "compare_releases",
    "evaluate_release_prerequisites",
    "is_release_compatible",
    "normalize_release",
    "parse_release_family",
    "resolve_workspace",
    "translate_workspace_url",
]
