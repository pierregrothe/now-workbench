"""Pydantic models for use-case-driven demo bundle synthesis."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UseCaseSynthesisRequest(BaseModel):
    """Input specification describing a customer use case and context."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    use_case: str = Field(..., description="Description of the business/technical use case")
    customer_name: str = Field(default="Acme Global", description="Target customer organization")
    industry: str = Field(default="Enterprise IT", description="Customer industry vertical")
    bundle_id: str | None = Field(default=None, description="Optional explicit bundle slug")
    sn_release: str | None = Field(
        default=None,
        description="Release to build for; omitted means the target instance's detected release",
    )
    instance_id: str | None = Field(
        default=None, description="Target instance; omitted means the default instance"
    )
    primary_color: str = Field(default="#23a17e", description="Customer brand accent hex")
    persona_primary: str = Field(
        default="Sarah Jenkins (Service Desk Lead)",
        description="Primary presenter persona",
    )
    persona_secondary: str = Field(
        default="Marcus Vance (Platform Architect)",
        description="Secondary technical persona",
    )


class SynthesizedDemoResult(BaseModel):
    """Output summary of a synthesized demonstration package."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_id: str
    bundle_path: str
    title: str
    customer_name: str
    industry: str
    fluent_table_name: str
    fluent_code: str
    seed_records: list[dict[str, Any]]
    sys_properties: dict[str, str]
    narrative_markdown: str
