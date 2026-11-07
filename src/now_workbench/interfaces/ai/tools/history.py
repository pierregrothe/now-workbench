# src/now_workbench/interfaces/ai/tools/history.py
# History tools: activity over time, drawn as chart tiles (ADR-027, ADR-028).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Usage, action, seed-run and team history for the Otto agent and the Actions screen.

Every figure comes from what the workbench records (telemetry, conversations, seed runs);
a day with no activity is a zero, never an estimate (ADR-013). The person sees their own
history; the team view is for administrators only.
"""

from datetime import date
from typing import Any

from now_workbench.domains.conversations import ThreadRepository
from now_workbench.domains.seed import SeedRepository
from now_workbench.domains.telemetry import TelemetryRepository, team_by_person
from now_workbench.interfaces.ai.tiles import UITileSpec
from now_workbench.interfaces.ai.tools.base import ToolContext, ToolResult, ToolSpec, register
from now_workbench.interfaces.ai.tools.charts import (
    DAYS_ARG,
    ChartSeries,
    ChartSpec,
    chart_tile,
    daily_series,
    day_label,
    fold_slices,
    history_days,
)

__all__: list[str] = []

# Fixed orders, so each key keeps its color whichever ones a period holds.
_SEED_STATUSES = {
    "completed": "Completed",
    "failed": "Failed",
    "rolled_back": "Rolled back",
    "rollback_failed": "Rollback failed",
}
_OUTCOMES = {"ok": "Succeeded", "failed": "Failed", "pending": "Awaiting confirmation"}
# Conversation totals and budgets count billable tokens (ADR-023); per-day figures are raw.
_BILLABLE = (
    "Conversation totals are billable tokens (input + output + 1.25 x cache writes + 0.1 x "
    "cache reads); tokens per day are raw counts by kind, so they add up to more."
)
_TOKEN_KINDS = {
    "input_tokens": "Input",
    "output_tokens": "Output",
    "cache_write": "Cache write",
    "cache_read": "Cache read",
}


def _per_day(days: list[date], series: list[ChartSeries], unit: str) -> ChartSpec:
    return ChartSpec(
        chart="bar", labels=[day_label(d) for d in days], series=series, stacked=True, unit=unit
    )


def _chart_data(days: list[date], series: list[ChartSeries]) -> dict[str, Any]:
    """Chart-ready data for Otto: every day (zeros included), one list per series."""
    return {
        "days": [day_label(d) for d in days],
        "per_day": {s.name: [int(v) for v in s.values] for s in series},
    }


def _token_tile(
    tile_id: str, title: str, days: list[date], daily: dict[str, dict[str, int]]
) -> tuple[UITileSpec | None, dict[str, Any]]:
    """Tokens per day, stacked by kind, or None when there was no Claude call."""
    counts = {(day, kind): n for day, kinds in daily.items() for kind, n in kinds.items() if n}
    series = daily_series(days, counts, _TOKEN_KINDS)
    if not series:
        return None, {}
    return chart_tile(tile_id, title, _per_day(days, series, "tokens")), _chart_data(days, series)


def _usage_history(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    days = history_days(args)
    repo = ThreadRepository(ctx.conn)
    per_day = repo.daily_question_counts(days[0].isoformat())
    counts = [float(per_day.get(d.isoformat(), 0)) for d in days]
    questions = ChartSpec(
        chart="area",
        labels=[day_label(d) for d in days],
        series=[ChartSeries(name="Questions", values=counts)],
    )
    tiles = [chart_tile("usage-questions", f"Questions per day, last {len(days)} days", questions)]
    own = TelemetryRepository(ctx.conn).daily_tokens(days[0].isoformat())
    tokens, token_data = _token_tile("usage-tokens-daily", "Tokens per day", days, own)
    if tokens is not None:
        tiles.append(tokens)
    threads = repo.list_threads()
    used = [(t.title[:40] or "Untitled", float(t.tokens_used)) for t in threads if t.tokens_used]
    if used:
        labels, values = fold_slices(used)
        share = ChartSpec(
            chart="donut",
            labels=labels,
            series=[ChartSeries(name="Tokens", values=values)],
            unit="tokens",
        )
        tiles.append(chart_tile("usage-tokens", "Billable tokens by conversation", share, span=1))
    here = next((t for t in threads if t.id == ctx.thread_id), None)
    if here is not None:
        meter = ChartSpec(chart="meter", value=here.tokens_used, max=here.max_tokens, unit="tokens")
        tiles.append(
            chart_tile("usage-limit", "This conversation's budget (billable tokens)", meter, span=1)
        )
    return ToolResult(
        summary=(
            f"{int(sum(counts))} question(s) in the last {len(days)} days; "
            f"{int(sum(v for _, v in used))} billable tokens across {len(used)} conversation(s). "
            + _BILLABLE
        ),
        data={
            "questions_per_day": {d.isoformat(): int(counts[i]) for i, d in enumerate(days)},
            "tokens_per_day": token_data,
            "billable_tokens_by_conversation": dict(used),
        },
        tiles=tiles,
        layout="2-col",
    )


def _seed_activity(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    days = history_days(args)
    counts = SeedRepository(ctx.conn).daily_status_counts(days[0].isoformat())
    series = daily_series(days, counts, _SEED_STATUSES)
    if not series:
        return ToolResult(summary=f"No seed runs in the last {len(days)} days.")
    by_status = {s.name: int(sum(s.values)) for s in series}
    return ToolResult(
        summary=f"{sum(counts.values())} seed run(s) in the last {len(days)} days: "
        + ", ".join(f"{n} {name.lower()}" for name, n in by_status.items())
        + ".",
        data={"runs_by_status": by_status, **_chart_data(days, series)},
        tiles=[
            chart_tile(
                "seed-history",
                f"Seed runs per day, last {len(days)} days",
                _per_day(days, series, "runs"),
            )
        ],
    )


def _action_history(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    days = history_days(args)
    repo = TelemetryRepository(ctx.conn)
    since = days[0].isoformat()
    series = daily_series(days, repo.daily_actions(since), _OUTCOMES)
    if not series:
        return ToolResult(summary=f"No actions run in the last {len(days)} days.")
    totals = repo.action_totals(since)
    top = totals[:8]
    most_used = ChartSpec(
        chart="bar",
        labels=[t["name"] for t in top],
        series=[ChartSeries(name="Runs", values=[float(t["runs"]) for t in top])],
        unit="runs",
    )
    runs = sum(t["runs"] for t in totals)
    failed = sum(t["failed"] for t in totals)
    return ToolResult(
        summary=f"{runs} action run(s) in the last {len(days)} days, {failed} failed.",
        data={"actions": totals, **_chart_data(days, series)},
        tiles=[
            chart_tile("actions-daily", "Actions per day", _per_day(days, series, "runs")),
            chart_tile("actions-top", "Most used actions", most_used),
        ],
        layout="2-col",
    )


def _person_chart(tile_id: str, title: str, by_person: dict[str, int], unit: str) -> UITileSpec:
    labels, values = fold_slices([(email, float(n)) for email, n in by_person.items()])
    spec = ChartSpec(
        chart="bar", labels=labels, series=[ChartSeries(name=unit, values=values)], unit=unit
    )
    return chart_tile(tile_id, title, spec)


def _team_usage(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    days = history_days(args)
    tokens, actions = team_by_person(ctx.conn, ctx.actor(), days[0].isoformat())
    tiles: list[UITileSpec] = []
    team = TelemetryRepository(ctx.conn).daily_tokens(days[0].isoformat(), everyone=True)
    daily, token_data = _token_tile("team-tokens-daily", "Team tokens per day", days, team)
    if daily is not None:
        tiles.append(daily)
    if tokens:
        tiles.append(_person_chart("team-tokens", "Tokens by person", tokens, "tokens"))
    if actions:
        tiles.append(_person_chart("team-actions", "Actions by person", actions, "runs"))
    return ToolResult(
        summary=(
            f"Last {len(days)} days: {sum(tokens.values())} tokens and "
            f"{sum(actions.values())} action run(s) across {len(tokens.keys() | actions.keys())} "
            "person(s)."
        ),
        data={"tokens_by_person": tokens, "actions_by_person": actions, "tokens": token_data},
        tiles=tiles,
        layout="2-col",
    )


_HISTORY = (
    (
        "usage_history",
        "Chart the person's own use of Otto: questions per day, tokens per day by kind (input, "
        "output, cache; raw counts), billable tokens by conversation, and this conversation's "
        "budget in billable tokens.",
        _usage_history,
        False,
    ),
    (
        "seed_activity",
        "Chart the person's seed runs per day by outcome (completed, failed, rolled back).",
        _seed_activity,
        False,
    ),
    (
        "action_history",
        "Chart the actions the person ran (by Otto or by hand) per day by outcome, and the most "
        "used actions; the data lists each action's runs, failures and mean duration.",
        _action_history,
        False,
    ),
    (
        "team_usage",
        "Administrators only: chart the whole team's tokens per day, tokens by person and "
        "actions by person.",
        _team_usage,
        True,
    ),
)

for _name, _description, _handler, _admin in _HISTORY:
    register(
        ToolSpec(
            name=_name,
            description=_description,
            properties={"days": DAYS_ARG},
            handler=_handler,
            category="history",
            admin_only=_admin,
        )
    )
