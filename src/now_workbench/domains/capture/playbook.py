"""Declarative Demo Playbook specifications and Pydantic v2 models."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PlaybookActionType(StrEnum):
    """Supported interactive actions in a demo playbook."""

    AUTHENTICATE = "authenticate"
    NAVIGATE = "navigate"
    MOVE_AND_CLICK = "move_and_click"
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    SCROLL = "scroll"
    HOVER = "hover"
    WAIT_FOR = "wait_for"
    ASSERT_TEXT = "assert_text"
    AI_TRIAGE = "ai_triage"


class PlaybookStep(BaseModel):
    """A single executable step within a demonstration playbook."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(description="Unique step identifier, e.g. step-1")
    action: PlaybookActionType = Field(description="Action verb to perform")
    description: str = Field(description="Human-readable step objective")
    selector: str | None = Field(default=None, description="DOM or Shadow-DOM selector")
    text: str | None = Field(default=None, description="Text to type, select, or assert")
    path: str | None = Field(default=None, description="URL or URI path for navigation")
    wait_ms: int = Field(default=400, description="Dwell time in milliseconds after action")
    timeout_ms: int = Field(default=10000, description="Maximum wait time for element")
    optional: bool = Field(default=False, description="Continue playbook if step fails")


class DemoPlaybook(BaseModel):
    """Complete declarative interactive walkthrough playbook for a demo bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_id: str = Field(description="Target demonstration bundle ID")
    title: str = Field(description="Title of the walkthrough demonstration")
    start_path: str = Field(default="/incident_list.do", description="Starting URL path")
    persona: str | None = Field(default=None, description="ServiceNow user to impersonate")
    steps: list[PlaybookStep] = Field(default_factory=list, description="Ordered steps")


class PlaybookStepResult(BaseModel):
    """Outcome of executing a single playbook step."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    step_id: str
    action: str
    description: str
    status: Literal["passed", "failed", "skipped"]
    duration_ms: int = 0
    error_message: str | None = None
    screenshot_file: str | None = None


class PlaybookExecutionResult(BaseModel):
    """Overall outcome of running a demonstration playbook."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_id: str
    playbook_title: str
    success: bool
    total_steps: int
    passed_steps: int
    step_results: list[PlaybookStepResult] = Field(default_factory=list)
    video_file: str | None = None
    thumbnail_file: str | None = None
    live_authenticated: bool = False
    duration_ms: int = 0
    started_at: str = ""
    completed_at: str = ""
