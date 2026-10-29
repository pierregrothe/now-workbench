"""Data models for demonstration configuration bundles."""

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class DemoPersona(BaseModel):
    """Demo user persona for walkthrough and impersonation."""

    name: str
    role: str
    email: str
    avatar_url: str | None = None
    notes: str = ""


class DemoManifest(BaseModel):
    """Manifest describing a demonstration package."""

    id: str = Field(..., description="Unique alphanumeric identifier (e.g. customer-service-ai)")
    name: str = Field(..., description="Display title for the demonstration")
    version: str = Field(default="1.0.0", description="Semantic or CalVer version")
    description: str = Field(default="", description="Summary of the demo narrative")
    author: str = Field(default="", description="Creator or team")
    sn_release: str = Field(default="Xanadu", description="Target ServiceNow release")
    required_plugins: list[str] = Field(default_factory=list, description="Plugin dependency IDs")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")
    personas: list[DemoPersona] = Field(default_factory=list, description="Key walkthrough personas")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class DemoBundleInfo(BaseModel):
    """Runtime metadata describing an extracted or discovered bundle."""

    manifest: DemoManifest
    bundle_path: str
    fluent_files: list[str] = Field(default_factory=list)
    seed_files: list[str] = Field(default_factory=list)
    has_walkthrough: bool = False
    sys_properties: dict[str, Any] = Field(default_factory=dict)
