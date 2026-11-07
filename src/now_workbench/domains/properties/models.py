"""Pydantic models for ServiceNow system property management and snapshots."""

from pydantic import BaseModel, ConfigDict, Field


class PropertyRecord(BaseModel):
    """Represents a single ServiceNow sys_properties record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    value: str
    description: str = ""


class PropertySnapshot(BaseModel):
    """Snapshot of system property states prior to demo bundle application."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    bundle_id: str
    instance_id: str
    timestamp: str
    original_values: dict[str, str | None] = Field(default_factory=dict)


class PropertyApplyResult(BaseModel):
    """Result of applying or restoring demo bundle system properties."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    success: bool
    applied_count: int
    restored_count: int = 0
    details: list[str] = Field(default_factory=list)
