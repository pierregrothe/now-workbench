"""Pydantic models for database entities in now-workbench."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class InstanceRecord(BaseModel):
    """Registered ServiceNow instance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    url: str
    username: str = "admin"
    password: str = ""
    auth_type: str = "basic"
    release: str = "Zurich"
    is_default: bool = False
    status: str = "unknown"
    last_checked: datetime | None = None


class InstanceCreate(BaseModel):
    """Payload to register a new ServiceNow instance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str | None = None
    name: str
    url: str
    username: str = "admin"
    password: str = ""
    auth_type: str = "basic"
    release: str = "Zurich"
    is_default: bool = False


class InstanceUpdate(BaseModel):
    """Payload to update an existing ServiceNow instance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str | None = None
    url: str | None = None
    username: str | None = None
    password: str | None = None
    auth_type: str | None = None
    release: str | None = None
    is_default: bool | None = None


class TemplateRecord(BaseModel):
    """Reusable customization template with customer placeholders."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    description: str
    version: str = "1.0.0"
    base_bundle_id: str
    parameters_schema: dict[str, Any] = Field(default_factory=dict)


class TemplateInstantiationRequest(BaseModel):
    """Request to instantiate a customization template for a customer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_bundle_id: str
    customer_name: str
    primary_color: str = "#23a17e"
    secondary_color: str = "#0284c7"
    logo_url: str = ""
    assignment_group: str = "IT Support Tier 1"


MAX_THREAD_CONTEXT_MESSAGES = 20


class ChatThreadRecord(BaseModel):
    """Conversational thread metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    archived: bool = False
    target_tab: str = "home"
    message_count: int = 0
    max_messages: int = MAX_THREAD_CONTEXT_MESSAGES
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ChatThreadCreate(BaseModel):
    """Payload to create a new conversational thread."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str | None = None
    title: str = "Workspace Orchestration Session"
    target_tab: str = "home"


class ChatThreadUpdate(BaseModel):
    """Payload to update or archive/unarchive a conversational thread."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str | None = None
    archived: bool | None = None
    target_tab: str | None = None


class ChatMessageCreate(BaseModel):
    """Payload to append a message to a conversational thread."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str
    role: str = "user"
    widget_type: str | None = None
    widget_data: dict[str, Any] | None = None


class ChatMessageRecord(BaseModel):
    """Chat message in a conversational thread."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    thread_id: str
    role: str
    content: str
    widget_type: str | None = None
    widget_data: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SeedRecordItem(BaseModel):
    """An individual record created during a seed operation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    table: str
    sys_id: str


class SeedOperationRecord(BaseModel):
    """Audit log of a seed run with rollback tracking."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    bundle_id: str
    instance_id: str
    status: str = "completed"
    created_records: list[SeedRecordItem] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class WorkbenchPreferences(BaseModel):
    """Persisted user preferences and defaults for Now Workbench."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # 1. Claude AI & Conversational Intent Router
    anthropic_api_key_masked: str = ""
    has_anthropic_api_key: bool = False
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
    default_sn_release: str = "Zurich"
    default_scoped_prefix: str = "x_snc"
    default_brand_color: str = "#62d84e"
    narrative_tone: str = "executive"

    # 4. Fluent SDK, UI & Presenter HUD
    sdk_fake_mode: bool = False
    show_welcome_on_startup: bool = True
    sidebar_collapsed_default: bool = False
    hud_font_scale: str = "standard"
    theme_mode: str = "system"
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
    default_sn_release: str | None = None
    default_scoped_prefix: str | None = None
    default_brand_color: str | None = None
    narrative_tone: str | None = None

    sdk_fake_mode: bool | None = None
    show_welcome_on_startup: bool | None = None
    sidebar_collapsed_default: bool | None = None
    hud_font_scale: str | None = None
    theme_mode: str | None = None
