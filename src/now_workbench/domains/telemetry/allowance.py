# src/now_workbench/domains/telemetry/allowance.py
# Monthly Claude allowance per person: warn at 80%, refuse at 100%, administrators exempt.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Usage allowance (ADR-031).

Each person may use a monthly allowance of billable Claude tokens, counted from recorded
telemetry the way the conversation budget counts them. The check runs before Otto calls
Claude, never by asking Claude. Administrators are exempt; under "view as" the person viewed
is checked, as they would be.
"""

import sqlite3
from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from now_workbench.domains.identity import AuthUser, is_admin
from now_workbench.domains.telemetry.repository import TelemetryRepository

__all__ = ["check_allowance", "Allowance", "WARN_AT_PERCENT"]

WARN_AT_PERCENT = 80

AllowanceState = Literal["exempt", "ok", "warn", "refused"]


class Allowance(BaseModel):
    """Where a person stands against their monthly allowance.

    Attributes:
        state: exempt (administrator), ok, warn (80% or more) or refused (100% or more).
        used: Billable tokens this UTC month.
        allowance: The monthly allowance.
        resets_on: First day of next month (UTC), when `used` starts again from zero.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    state: AllowanceState
    used: int
    allowance: int
    resets_on: date

    @property
    def percent(self) -> int:
        """Whole percent of the allowance used (floored, so 79.9% reads 79)."""
        return self.used * 100 // self.allowance

    def message(self) -> str:
        """What to tell the person; empty when there is nothing to say."""
        reset = f"{self.resets_on:%B} {self.resets_on.day}"
        if self.state == "refused":
            return (
                f"You have used your monthly Claude allowance ({self.allowance:,} tokens). "
                f"It resets on {reset}; an administrator can raise it."
            )
        if self.state == "warn":
            return (
                f"You have used {self.percent}% of your monthly Claude allowance "
                f"({self.used:,} of {self.allowance:,} tokens). It resets on {reset}."
            )
        return ""


def _month_bounds(now: datetime) -> tuple[str, date]:
    """This UTC month's first instant (as stored timestamps read) and next month's first day."""
    since = f"{now.year:04d}-{now.month:02d}-01T00:00:00.000Z"
    return since, date(now.year + now.month // 12, now.month % 12 + 1, 1)


def check_allowance(
    conn: sqlite3.Connection, user: AuthUser, allowance: int, now: datetime
) -> Allowance:
    """Where `user` stands this month (the owner scope must be `user`'s).

    Args:
        conn: Open connection.
        user: The person asking (after "view as").
        allowance: Monthly allowance in billable tokens.
        now: The current time (UTC).

    Returns:
        The person's standing; administrators are always `exempt`.
    """
    since, resets_on = _month_bounds(now.astimezone(UTC))
    used = TelemetryRepository(conn).billable_since(since)
    if is_admin(user):
        state: AllowanceState = "exempt"
    elif used >= allowance:
        state = "refused"
    elif used * 100 >= allowance * WARN_AT_PERCENT:
        state = "warn"
    else:
        state = "ok"
    return Allowance(state=state, used=used, allowance=allowance, resets_on=resets_on)
