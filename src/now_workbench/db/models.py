"""Pydantic models for database entities in now-workbench."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

UNKNOWN_RELEASE = "Unknown"

# What the owner uses the instance for. Declared, never detected: ServiceNow reports how an
# instance was provisioned (a standalone demo reports "prod"), not what it is for.
InstancePurpose = Literal["demo", "development", "test", "production"]
INSTANCE_PURPOSES: tuple[InstancePurpose, ...] = ("demo", "development", "test", "production")


class InstanceNode(BaseModel):
    """One application node of an instance, as reported by sys_cluster_state (ADR-014)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str
    hostname: str
    datacenter: str | None = None
    status: str
    cpu_count: int | None = None
    memory_max_mb: float | None = None
    memory_in_use_mb: float | None = None
    memory_pressure: str | None = None
    started_at: datetime | None = None


class InstanceProfile(BaseModel):
    """Platform facts read from the instance at connection time (ADR-014).

    Every field is optional: what can be read depends on the account's roles
    (``sys_properties`` vs. the admin-only cluster tables).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    instance_id: str
    release: str | None = None
    build_tag: str | None = None
    build_date: str | None = None
    platform_name: str | None = None
    installation_name: str | None = None
    # Platform-reported provisioning facts -- NOT the owner's intent (see InstancePurpose).
    instance_type: str | None = None
    production_property: bool | None = None
    datacenter: str | None = None
    db_product: str | None = None
    db_version: str | None = None
    java_version: str | None = None
    os: str | None = None
    nodes: list[InstanceNode] = Field(default_factory=list)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class InstanceRecord(BaseModel):
    """Registered ServiceNow instance with decrypted credentials (backend use only).

    Never return this model from an API route: use ``InstancePublic`` (ADR-012).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    url: str
    username: str = "admin"
    password: str = ""
    auth_type: str = "basic"
    release: str = UNKNOWN_RELEASE  # read-only: from the detected profile (ADR-014)
    purpose: InstancePurpose = "demo"
    is_default: bool = False
    status: str = "unknown"
    last_checked: datetime | None = None

    def to_public(self, profile: InstanceProfile | None = None) -> InstancePublic:
        """Return the API-safe view of this instance (password withheld)."""
        return InstancePublic(
            id=self.id,
            name=self.name,
            url=self.url,
            username=self.username,
            has_password=bool(self.password),
            auth_type=self.auth_type,
            release=self.release,
            purpose=self.purpose,
            is_default=self.is_default,
            status=self.status,
            last_checked=self.last_checked,
            profile=profile,
        )


class InstancePublic(BaseModel):
    """API-safe view of a registered instance: the password never leaves the backend."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    url: str
    username: str
    has_password: bool
    auth_type: str
    release: str
    purpose: InstancePurpose
    is_default: bool
    status: str
    last_checked: datetime | None = None
    profile: InstanceProfile | None = None


class InstanceCreate(BaseModel):
    """Payload to register a new ServiceNow instance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str | None = None
    name: str
    url: str
    username: str = "admin"
    password: str = ""
    auth_type: str = "basic"
    purpose: InstancePurpose = "demo"
    is_default: bool = False


class InstanceUpdate(BaseModel):
    """Payload to update an existing ServiceNow instance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str | None = None
    url: str | None = None
    username: str | None = None
    password: str | None = None
    auth_type: str | None = None
    purpose: InstancePurpose | None = None
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
    attachment_ids: list[str] = Field(default_factory=list, max_length=50)


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
