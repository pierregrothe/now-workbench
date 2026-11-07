# src/now_workbench/domains/telemetry/models.py
# Telemetry records: one Claude call, one action run (ADR-028).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Telemetry models.

`owner_email` is whose data it is (the person, or the person an administrator views as);
`actor_email` is who really acted, so usage under "view as" stays attributable.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ActionEvent", "UsageEvent", "ActionOutcome", "ActionSource"]

ActionSource = Literal["otto", "actions"]
ActionOutcome = Literal["ok", "failed", "pending"]


class UsageEvent(BaseModel):
    """Tokens of one Claude call Otto made."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    owner_email: str = Field(min_length=1)
    actor_email: str = Field(min_length=1)
    thread_id: str = ""
    model: str = Field(min_length=1)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cache_write: int = Field(default=0, ge=0)
    cache_read: int = Field(default=0, ge=0)


class ActionEvent(BaseModel):
    """One run of an action (a tool), by Otto or by hand on the Actions screen."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    owner_email: str = Field(min_length=1)
    actor_email: str = Field(min_length=1)
    name: str = Field(min_length=1)
    source: ActionSource
    outcome: ActionOutcome
    duration_ms: int = Field(ge=0)
