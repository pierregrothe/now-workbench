"""Data models for ServiceNow platform releases and workspace evolutions."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
