"""Data models for demonstration configuration bundles."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DemoPersona(BaseModel):
    """Demo user persona for walkthrough and impersonation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    role: str
    email: str
    avatar_url: str | None = None
    notes: str = ""


class DemoManifest(BaseModel):
    """Manifest describing a demonstration package."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., description="Unique alphanumeric identifier (e.g. customer-service-ai)")
    name: str = Field(..., description="Display title for the demonstration")
    version: str = Field(default="1.0.0", description="Semantic or CalVer version")
    description: str = Field(default="", description="Summary of the demo narrative")
    author: str = Field(default="", description="Creator or team")
    min_release: str = Field(
        default="Xanadu", description="Minimum ServiceNow release required for this demo"
    )
    sn_release: str = Field(
        default="Xanadu", description="Target/tested ServiceNow release (legacy compatibility)"
    )
    required_plugins: list[str] = Field(default_factory=list, description="Plugin dependency IDs")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")
    personas: list[DemoPersona] = Field(
        default_factory=list, description="Key walkthrough personas"
    )
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @model_validator(mode="before")
    @classmethod
    def _sync_release_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "min_release" in data and "sn_release" not in data:
                data["sn_release"] = data["min_release"]
            elif "sn_release" in data and "min_release" not in data:
                data["min_release"] = data["sn_release"]
        return data


class DemoBundleInfo(BaseModel):
    """Runtime metadata describing an extracted or discovered bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    manifest: DemoManifest
    bundle_path: str
    fluent_files: list[str] = Field(default_factory=list)
    seed_files: list[str] = Field(default_factory=list)
    has_walkthrough: bool = False
    sys_properties: dict[str, Any] = Field(default_factory=dict)
    media_captures: list[dict[str, Any]] = Field(default_factory=list)
