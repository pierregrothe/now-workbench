# src/now_workbench/domains/telemetry/repository.py
# Telemetry persistence and the aggregates the history charts read (ADR-028).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Telemetry repository.

Reads are scoped to the current owner unless `everyone` is set; only the team service
(administrators) sets it. The SQL lives in module constants, one per statement.
"""

from typing import Any

from now_workbench.domains.telemetry.models import (
    CACHE_READ_WEIGHT,
    CACHE_WRITE_WEIGHT,
    ActionEvent,
    UsageEvent,
)
from now_workbench.platform.db.repository import Repository
from now_workbench.platform.owner import current_owner

__all__ = ["TOKEN_KINDS", "TelemetryRepository"]

TOKEN_KINDS = ("input_tokens", "output_tokens", "cache_write", "cache_read")

_INSERT_USAGE = (
    "INSERT INTO usage_events (owner_email, actor_email, thread_id, model, input_tokens, "
    "output_tokens, cache_write, cache_read) VALUES (?, ?, ?, ?, ?, ?, ?, ?);"
)
_INSERT_ACTION = (
    "INSERT INTO action_events (owner_email, actor_email, name, source, outcome, duration_ms) "
    "VALUES (?, ?, ?, ?, ?, ?);"
)
# `{scope}` is empty (everyone) or the owner filter; `?` placeholders follow in that order.
_OWNER_SCOPE = "AND owner_email = ?"
# Retention (ADR-029): one statement per table, both run in one transaction.
_PURGE = (
    "DELETE FROM usage_events WHERE created_at < ?;",
    "DELETE FROM action_events WHERE created_at < ?;",
)
_DAILY_TOKENS = (
    "SELECT substr(created_at, 1, 10) AS day, "
    + ", ".join(f"SUM({k}) AS {k}" for k in TOKEN_KINDS)
    + " FROM usage_events WHERE created_at >= ? {scope} GROUP BY day;"
)
_DAILY_ACTIONS = (
    "SELECT substr(created_at, 1, 10) AS day, outcome, COUNT(*) AS n FROM action_events "
    "WHERE created_at >= ? {scope} GROUP BY day, outcome;"
)
_ACTION_TOTALS = (
    "SELECT name, COUNT(*) AS runs, SUM(outcome = 'failed') AS failed, "
    "CAST(AVG(duration_ms) AS INTEGER) AS avg_ms FROM action_events "
    "WHERE created_at >= ? {scope} GROUP BY name ORDER BY runs DESC, name;"
)
_TOKENS_BY_PERSON = (
    "SELECT owner_email AS who, SUM("
    + " + ".join(TOKEN_KINDS)
    + ") AS n FROM usage_events WHERE created_at >= ? {scope} GROUP BY owner_email;"
)
# Billable tokens as the conversation budget counts them (ADR-023), for the allowance.
_BILLABLE_SINCE = (
    "SELECT COALESCE(SUM(input_tokens + output_tokens"
    f" + {CACHE_WRITE_WEIGHT} * cache_write + {CACHE_READ_WEIGHT} * cache_read), 0) AS n"
    " FROM usage_events WHERE created_at >= ? {scope};"
)
_ACTIONS_BY_PERSON = (
    "SELECT owner_email AS who, COUNT(*) AS n FROM action_events "
    "WHERE created_at >= ? {scope} GROUP BY owner_email;"
)


class TelemetryRepository(Repository):
    """Record usage and action events; aggregate them per day, action and person."""

    def record_usage(self, event: UsageEvent) -> None:
        """Store the tokens of one Claude call."""
        with self.conn:
            self.conn.execute(
                _INSERT_USAGE,
                (
                    event.owner_email,
                    event.actor_email,
                    event.thread_id,
                    event.model,
                    event.input_tokens,
                    event.output_tokens,
                    event.cache_write,
                    event.cache_read,
                ),
            )

    def record_action(self, event: ActionEvent) -> None:
        """Store one action run."""
        with self.conn:
            self.conn.execute(
                _INSERT_ACTION,
                (
                    event.owner_email,
                    event.actor_email,
                    event.name,
                    event.source,
                    event.outcome,
                    event.duration_ms,
                ),
            )

    def purge_before(self, cutoff: str) -> int:
        """Delete every usage and action event recorded before `cutoff`.

        Args:
            cutoff: ISO timestamp (UTC); older events go.

        Returns:
            The number of events deleted.
        """
        with self.conn:
            return sum(self.conn.execute(sql, (cutoff,)).rowcount for sql in _PURGE)

    def _own(self, sql: str, since: str) -> list[Any]:
        """Run an aggregate over the owner's events from `since` on."""
        return self.conn.execute(
            sql.format(scope=_OWNER_SCOPE), (since, current_owner())
        ).fetchall()

    def _all(self, sql: str, since: str) -> list[Any]:
        """Run an aggregate over everyone's events from `since` on (team view)."""
        return self.conn.execute(sql.format(scope=""), (since,)).fetchall()

    def daily_tokens(self, since: str, everyone: bool = False) -> dict[str, dict[str, int]]:
        """Return tokens per UTC day and kind (input, output, cache write, cache read).

        Args:
            since: First day (YYYY-MM-DD).
            everyone: Every person's usage, not only the owner's.

        Returns:
            Token counts keyed by day, then by kind; days without calls are absent.
        """
        rows = self._all(_DAILY_TOKENS, since) if everyone else self._own(_DAILY_TOKENS, since)
        return {r[0]: {k: int(r[k]) for k in TOKEN_KINDS} for r in rows}

    def daily_actions(self, since: str) -> dict[tuple[str, str], int]:
        """Return the owner's action runs per UTC day and outcome (ok, failed, pending).

        Args:
            since: First day (YYYY-MM-DD).

        Returns:
            Run counts keyed by (day, outcome); empty combinations are absent.
        """
        return {(day, outcome): int(n) for day, outcome, n in self._own(_DAILY_ACTIONS, since)}

    def action_totals(self, since: str) -> list[dict[str, Any]]:
        """Return the owner's actions with runs, failures and mean duration, most used first.

        Args:
            since: First day (YYYY-MM-DD).

        Returns:
            One row per action: name, runs, failed, avg_ms.
        """
        return [dict(r) for r in self._own(_ACTION_TOTALS, since)]

    def billable_since(self, since: str) -> int:
        """Return the owner's billable tokens from `since` on, rounded to the nearest token.

        Args:
            since: First instant (ISO timestamp, UTC).

        Returns:
            Input + output + 1.25 x cache writes + 0.1 x cache reads.
        """
        return round(float(self._own(_BILLABLE_SINCE, since)[0][0]))

    def tokens_by_person(self, since: str) -> dict[str, int]:
        """Return every person's total tokens from `since` on (team view, administrators)."""
        return {who: int(n) for who, n in self._all(_TOKENS_BY_PERSON, since)}

    def actions_by_person(self, since: str) -> dict[str, int]:
        """Return every person's action runs from `since` on (team view, administrators)."""
        return {who: int(n) for who, n in self._all(_ACTIONS_BY_PERSON, since)}
