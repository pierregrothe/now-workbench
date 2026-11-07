"""Pydantic models for demonstration walkthrough runbooks and persona stages."""

from pydantic import BaseModel, ConfigDict, Field


class DemoPersona(BaseModel):
    """ServiceNow user persona represented in a demonstration walkthrough."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., description="Full persona name (e.g. Beth Anglin)")
    role: str = Field(default="Demonstration User", description="Persona business or platform role")
    email: str = Field(default="", description="Impersonation email or username")


class RunbookStage(BaseModel):
    """Individual demonstration stage with talking points, instructions, and target state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_number: int = Field(..., description="1-based sequence index")
    title: str = Field(..., description="Stage title")
    persona: str | None = Field(default=None, description="Active persona for this stage")
    instructions: list[str] = Field(
        default_factory=list, description="Step-by-step presenter actions"
    )
    talking_points: list[str] = Field(
        default_factory=list, description="Value proposition talking points"
    )
    target_table: str | None = Field(
        default=None, description="ServiceNow table to inspect or verify"
    )
    verification_query: str | None = Field(
        default=None, description="Table API sysparm_query condition"
    )


class RunbookGuide(BaseModel):
    """Complete parsed walkthrough guide for a demonstration package."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    bundle_id: str = Field(..., description="Associated demo bundle ID")
    title: str = Field(..., description="Demonstration guide title")
    narrative: str = Field(
        default="", description="Customer value narrative and high-level premise"
    )
    stages: list[RunbookStage] = Field(
        default_factory=list, description="Ordered demonstration stages"
    )
    personas: list[DemoPersona] = Field(
        default_factory=list, description="Extracted demonstration personas"
    )


class StageTestResult(BaseModel):
    """Result of verifying a single demonstration stage."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    step_number: int
    title: str
    target_table: str | None
    passed: bool
    message: str


class RunbookTestResult(BaseModel):
    """Overall result of executing an automated demo script runbook verification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    bundle_id: str
    instance_name: str
    total_stages: int
    passed_stages: int
    all_passed: bool
    stages: list[StageTestResult]
