"""Pydantic models for Playwright instance screenshot and video capture."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Viewport(BaseModel):
    """Browser viewport of a capture or a recorded walkthrough."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    width: int = Field(default=1280, ge=1)
    height: int = Field(default=720, ge=1)


class SignIn(BaseModel):
    """Credentials a capture signs in with; they go to the browser on stdin, never in argv."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    username: str = ""
    password: str = Field(default="", repr=False)


class CaptureRequest(BaseModel):
    """Request parameters to capture a screenshot or video of a ServiceNow instance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_id: str = Field(default="sample-ai-assistant", description="Associated demo bundle ID")
    instance_id: str | None = Field(default=None, description="Target registered instance ID")
    target_path: str = Field(
        default="/now/nav/ui/classic/params/target/incident_list.do",
        description="ServiceNow URI path to capture",
    )
    media_type: str = Field(
        default="screenshot",
        description="Capture format: screenshot (.png) or video (.webm)",
    )
    label: str = Field(
        default="Instance State Capture",
        description="Human-readable caption for the capture",
    )
    viewport_width: int = Field(default=1440, description="Browser viewport width")
    viewport_height: int = Field(default=900, description="Browser viewport height")
    fake_mode: bool = Field(
        default=False,
        description="Use deterministic simulated capture when offline",
    )


class CaptureArtifact(BaseModel):
    """Metadata describing a captured screenshot or video artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    bundle_id: str
    instance_url: str
    target_path: str
    media_type: str
    label: str
    filename: str
    file_path: str
    url: str
    engine: str = "playwright"
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    live_authenticated: bool = False
    step_results: list[dict[str, Any]] = Field(default_factory=list)
