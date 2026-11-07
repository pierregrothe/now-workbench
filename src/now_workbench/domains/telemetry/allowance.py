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

from now_workbench.domains.identity import AuthUser, Role, is_admin, list_team, require_admin
from now_workbench.domains.telemetry.repository import TelemetryRepository
from now_workbench.platform.errors import InvalidInputError, NotFoundError

__all__ = [
    "allowance_for",
    "check_allowance",
    "set_allowance_override",
    "team_allowances",
    "Allowance",
    "PersonAllowance",
    "MAX_ALLOWANCE",
    "MIN_ALLOWANCE",
    "WARN_AT_PERCENT",
]

WARN_AT_PERCENT = 80
MIN_ALLOWANCE = 100_000
MAX_ALLOWANCE = 1_000_000_000

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
    utc = now.astimezone(UTC)
    since = f"{utc.year:04d}-{utc.month:02d}-01T00:00:00.000Z"
    return since, date(utc.year + utc.month // 12, utc.month % 12 + 1, 1)


def _state(used: int, allowance: int, admin: bool) -> AllowanceState:
    if admin:
        return "exempt"
    if used >= allowance:
        return "refused"
    if used * 100 >= allowance * WARN_AT_PERCENT:
        return "warn"
    return "ok"


def allowance_for(conn: sqlite3.Connection, email: str, default: int) -> int:
    """The person's monthly allowance: an administrator's override, else the default."""
    override = TelemetryRepository(conn).allowance_override(email)
    return default if override is None else override


def check_allowance(
    conn: sqlite3.Connection, user: AuthUser, default: int, now: datetime
) -> Allowance:
    """Where `user` stands this month (the owner scope must be `user`'s).

    Args:
        conn: Open connection.
        user: The person asking (after "view as").
        default: The allowance for people without an override (billable tokens a month).
        now: The current time (UTC).

    Returns:
        The person's standing; administrators are always `exempt`.
    """
    since, resets_on = _month_bounds(now)
    used = TelemetryRepository(conn).billable_since(since)
    allowance = allowance_for(conn, user.email, default)
    return Allowance(
        state=_state(used, allowance, is_admin(user)),
        used=used,
        allowance=allowance,
        resets_on=resets_on,
    )


class PersonAllowance(Allowance):
    """One team member's standing, for the administrators' team view.

    Attributes:
        email: The person.
        overridden: An administrator set this person's allowance (else the default applies).
    """

    email: str
    overridden: bool


def team_allowances(
    conn: sqlite3.Connection, actor: AuthUser, default: int, now: datetime
) -> list[PersonAllowance]:
    """Every team member's use and allowance this month (administrators only).

    Raises:
        ForbiddenError: The actor is not an administrator.
    """
    members = list_team(conn, actor)
    repo = TelemetryRepository(conn)
    since, resets_on = _month_bounds(now)
    used = repo.billable_by_person(since)
    overrides = repo.allowance_overrides()
    rows = []
    for m in members:
        spent = used.get(m.email, 0)
        allowance = overrides.get(m.email, default)
        rows.append(
            PersonAllowance(
                email=m.email,
                overridden=m.email in overrides,
                state=_state(spent, allowance, Role.ADMIN in m.roles),
                used=spent,
                allowance=allowance,
                resets_on=resets_on,
            )
        )
    return rows


def set_allowance_override(
    conn: sqlite3.Connection, actor: AuthUser, email: str, tokens: int | None
) -> None:
    """Set a person's monthly allowance, or with None return them to the default.

    Raises:
        ForbiddenError: The actor is not an administrator.
        InvalidInputError: The amount is outside 100,000 to 1,000,000,000.
        NotFoundError: The person is not on the team.
    """
    require_admin(actor)
    if tokens is not None and not MIN_ALLOWANCE <= tokens <= MAX_ALLOWANCE:
        raise InvalidInputError(
            f"An allowance must be between {MIN_ALLOWANCE:,} and {MAX_ALLOWANCE:,} tokens."
        )
    if email not in {m.email for m in list_team(conn, actor)}:
        raise NotFoundError(f"{email} is not on the team.")
    TelemetryRepository(conn).put_allowance_override(email, tokens, actor.real_email or actor.email)
