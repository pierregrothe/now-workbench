"""Pydantic models for ServiceNow instance plugins and modules."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class PluginRecord(BaseModel):
    """Installed ServiceNow plugin or store module."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    instance_id: str
    plugin_id: str
    plugin_name: str
    status: str = "active"
    installed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class PluginEvaluationResult(BaseModel):
    """Result of evaluating required plugins against an instance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    instance_id: str
    required: list[str]
    installed: list[str]
    missing: list[str]
    all_satisfied: bool
