# src/now_workbench/domains/telemetry/service.py
# Recording telemetry for the person acting, and the team view for administrators (ADR-028).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Telemetry service.

The two `record_*` functions are the only writers; they are called where every Claude call
and every action run passes (the agent loop and `execute_tool`), so nothing can skip them.
Team aggregates are for administrators only, whoever asks (Otto, the Actions screen or the
API).
"""

import sqlite3
from datetime import datetime, timedelta

from now_workbench.domains.identity import AuthUser, require_admin
from now_workbench.domains.telemetry.models import (
    ActionEvent,
    ActionOutcome,
    ActionSource,
    UsageEvent,
)
from now_workbench.domains.telemetry.repository import TelemetryRepository
from now_workbench.platform.owner import current_owner

__all__ = ["purge_expired", "record_action", "record_usage", "team_by_person"]


def _actor_email(actor: AuthUser | None) -> str:
    """Who really acted: the administrator behind a "view as", else the person."""
    if actor is None:
        return current_owner()
    return actor.real_email or actor.email


def record_usage(
    conn: sqlite3.Connection,
    actor: AuthUser | None,
    model: str,
    counts: dict[str, int],
    thread_id: str = "",
) -> None:
    """Record the tokens of one Claude call for the current owner.

    Args:
        conn: Open connection.
        actor: The signed-in person (None outside a request: the owner acts).
        model: Model that answered.
        counts: Token counts with keys input, output, cache_write, cache_read.
        thread_id: The conversation the call answered in, if any.
    """
    TelemetryRepository(conn).record_usage(
        UsageEvent(
            owner_email=current_owner(),
            actor_email=_actor_email(actor),
            thread_id=thread_id,
            model=model,
            input_tokens=counts.get("input", 0),
            output_tokens=counts.get("output", 0),
            cache_write=counts.get("cache_write", 0),
            cache_read=counts.get("cache_read", 0),
        )
    )


def record_action(
    conn: sqlite3.Connection,
    actor: AuthUser | None,
    name: str,
    source: ActionSource,
    outcome: ActionOutcome,
    duration_ms: int,
) -> None:
    """Record one action run for the current owner.

    Args:
        conn: Open connection.
        actor: The signed-in person (None outside a request: the owner acts).
        name: The action (tool) name.
        source: Who started it: Otto, or the person on the Actions screen.
        outcome: ok, failed, or pending (waiting for confirmation).
        duration_ms: Wall-clock time of the run.
    """
    TelemetryRepository(conn).record_action(
        ActionEvent(
            owner_email=current_owner(),
            actor_email=_actor_email(actor),
            name=name,
            source=source,
            outcome=outcome,
            duration_ms=max(0, duration_ms),
        )
    )


def team_by_person(
    conn: sqlite3.Connection, actor: AuthUser, since: str
) -> tuple[dict[str, int], dict[str, int]]:
    """Return every person's tokens and action runs from `since` on.

    Args:
        conn: Open connection.
        actor: The signed-in person; must be an administrator.
        since: First day (YYYY-MM-DD).

    Returns:
        (tokens by person, action runs by person).

    Raises:
        ForbiddenError: The person is not an administrator.
    """
    require_admin(actor)
    repo = TelemetryRepository(conn)
    return repo.tokens_by_person(since), repo.actions_by_person(since)


def purge_expired(conn: sqlite3.Connection, retention_days: int, now: datetime) -> int:
    """Delete everyone's telemetry older than the retention window (ADR-029).

    Args:
        conn: Open connection.
        retention_days: Days of events to keep, ending at `now`.
        now: The current UTC time.

    Returns:
        The number of events deleted.
    """
    cutoff = now - timedelta(days=retention_days)
    return TelemetryRepository(conn).purge_before(cutoff.strftime("%Y-%m-%dT%H:%M:%S.000Z"))
