# src/now_workbench/platform/clock.py
# The one place the current UTC time is read for mutation-gated modules (ADR-029).
# Author: Pierre Grothe
# Date: 2026-11-07
"""UTC clock.

`datetime.now(UTC)` inline lets a mutation (`now(None)`) survive whenever the local and UTC
dates agree, so the mutation gate would pass or fail with the time of day. Reading the time
here keeps those modules deterministic under mutation.
"""

from datetime import UTC, datetime

__all__ = ["utc_now"]


def utc_now() -> datetime:
    """Return the current time, timezone-aware in UTC."""
    return datetime.now(UTC)
