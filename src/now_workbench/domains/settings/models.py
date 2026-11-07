# src/now_workbench/domains/settings/models.py
# Per-user workbench preferences.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Preference models."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "WorkbenchPreferences",
    "WorkbenchPreferencesUpdate",
]


class WorkbenchPreferences(BaseModel):
    """Persisted user preferences and defaults for Now Workbench."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # 1. Claude AI & Conversational Intent Router
    anthropic_api_key_masked: str = ""
    has_anthropic_api_key: bool = False
    anthropic_api_key_from_env: bool = False
    claude_model: str = "claude-sonnet-5-5"
    auto_route_intent: bool = True
    auto_execute_intent: bool = True

    # 2. Playwright Media Capture Defaults
    capture_viewport_width: int = 1440
    capture_viewport_height: int = 900
    capture_default_media_type: str = "screenshot"
    capture_wait_timeout_ms: int = 1500
    capture_fake_mode: bool = False

    # 3. Solution Consultant & Synthesis Defaults
    sc_author_name: str = "Now Workbench Solution Consultant"
    sc_author_email: str = "sc@servicenow.com"
    default_scoped_prefix: str = "x_snc"
    default_brand_color: str = "#62d84e"
    narrative_tone: str = "executive"

    # 4. Fluent SDK, UI & Presenter HUD
    sdk_fake_mode: bool = False
    show_welcome_on_startup: bool = True
    sidebar_collapsed_default: bool = False
    hud_font_scale: str = "standard"
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class WorkbenchPreferencesUpdate(BaseModel):
    """Partial update payload for Now Workbench preferences."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    anthropic_api_key: str | None = None
    claude_model: str | None = None
    auto_route_intent: bool | None = None
    auto_execute_intent: bool | None = None

    capture_viewport_width: int | None = None
    capture_viewport_height: int | None = None
    capture_default_media_type: str | None = None
    capture_wait_timeout_ms: int | None = None
    capture_fake_mode: bool | None = None

    sc_author_name: str | None = None
    sc_author_email: str | None = None
    default_scoped_prefix: str | None = None
    default_brand_color: str | None = None
    narrative_tone: str | None = None

    sdk_fake_mode: bool | None = None
    show_welcome_on_startup: bool | None = None
    sidebar_collapsed_default: bool | None = None
    hud_font_scale: str | None = None
