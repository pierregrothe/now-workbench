# src/now_workbench/domains/seed/models.py
# Seed operations and the records they created, for rollback.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Seed models."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "SeedOperationRecord",
    "SeedRecordItem",
]


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
    error: str = ""
