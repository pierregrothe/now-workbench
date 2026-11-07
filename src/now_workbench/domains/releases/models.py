# src/now_workbench/domains/releases/models.py
# ServiceNow release families, compatibility results and workspace routes.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Data models for ServiceNow platform releases and workspace evolutions."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "RELEASE_FAMILIES",
    "ReleaseCompatibilityResult",
    "UNKNOWN_RELEASE",
    "WorkspaceCategory",
    "WorkspaceRoute",
]

# Historical releases in chronological order. Used ONLY to order the release names that
# requirements mention (bundle min_release, feature minimums). An instance reports its
# own release at connection (ADR-014); a name missing here is, by construction, newer
# than every entry, so a new ServiceNow release never requires a code change.
RELEASE_FAMILIES: tuple[str, ...] = (
    "Rome",
    "San Diego",
    "Tokyo",
    "Utah",
    "Vancouver",
    "Washington DC",
    "Xanadu",
    "Yokohama",
    "Zurich",
    "Australia",
)

WorkspaceCategory = Literal["itsm", "csm", "hr", "ai_studio", "classic"]


class ReleaseCompatibilityResult(BaseModel):
    """Result of evaluating platform release compatibility."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    is_compatible: bool
    instance_release: str
    min_release: str
    reason: str
    required_features: list[str] = Field(default_factory=list)
    unsupported_features: list[str] = Field(default_factory=list)


class WorkspaceRoute(BaseModel):
    """Information about a version-specific ServiceNow workspace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    workspace_type: str
    release: str
    display_name: str
    path: str
    is_available: bool = True
    description: str = ""


UNKNOWN_RELEASE = "Unknown"
