# src/now_workbench/interfaces/ai/tools/history.py
# History tools: the person's own activity over time, drawn as chart tiles (ADR-027).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Usage and seed-run history for the Otto agent and the Actions screen.

Every figure comes from what the workbench stores for the signed-in person; a day with no
activity is a zero, never an estimate (ADR-013).
"""

from datetime import UTC, date, datetime, timedelta
from typing import Any

from now_workbench.domains.conversations import ThreadRepository
from now_workbench.domains.seed import SeedRepository
from now_workbench.interfaces.ai.tools.base import ToolContext, ToolResult, ToolSpec, register
from now_workbench.interfaces.ai.tools.charts import (
    MAX_POINTS,
    ChartSeries,
    ChartSpec,
    chart_tile,
    fold_slices,
)

__all__: list[str] = []

_DAYS_ARG = {
    "type": "integer",
    "minimum": 1,
    "maximum": MAX_POINTS,
    "description": f"Days of history, ending today (default 30, at most {MAX_POINTS}).",
}
# Seed statuses in a fixed order, so each keeps its color whichever ones a period holds.
_SEED_STATUSES = ("completed", "failed", "rolled_back", "rollback_failed")


def _days(args: dict[str, Any]) -> list[date]:
    """The UTC days the history covers, oldest first."""
    n = min(max(int(args.get("days") or 30), 1), MAX_POINTS)
    today = datetime.now(UTC).date()
    return [today - timedelta(days=i) for i in range(n - 1, -1, -1)]


def _label(day: date) -> str:
    return day.strftime("%b %d")


def _usage_history(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    days = _days(args)
    repo = ThreadRepository(ctx.conn)
    per_day = repo.daily_question_counts(days[0].isoformat())
    counts = [float(per_day.get(d.isoformat(), 0)) for d in days]
    questions = ChartSpec(
        chart="area",
        labels=[_label(d) for d in days],
        series=[ChartSeries(name="Questions", values=counts)],
    )
    tiles = [chart_tile("usage-questions", f"Questions per day, last {len(days)} days", questions)]
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
        tiles.append(chart_tile("usage-tokens", "Tokens by conversation", share, span=1))
    here = next((t for t in threads if t.id == ctx.thread_id), None)
    if here is not None:
        meter = ChartSpec(chart="meter", value=here.tokens_used, max=here.max_tokens, unit="tokens")
        tiles.append(chart_tile("usage-limit", "This conversation's token budget", meter, span=1))
    total_tokens = sum(v for _, v in used)
    return ToolResult(
        summary=(
            f"{int(sum(counts))} question(s) in the last {len(days)} days; "
            f"{int(total_tokens)} tokens across {len(used)} conversation(s)."
        ),
        data={
            "questions_per_day": {d.isoformat(): int(c) for d, c in zip(days, counts, strict=True)},
            "tokens_by_conversation": dict(used),
        },
        tiles=tiles,
        layout="2-col",
    )


def _seed_activity(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    days = _days(args)
    counts = SeedRepository(ctx.conn).daily_status_counts(days[0].isoformat())
    present = [s for s in _SEED_STATUSES if any(k[1] == s for k in counts)]
    present += sorted({k[1] for k in counts} - set(present))
    series = [
        ChartSeries(
            name=status.replace("_", " ").capitalize(),
            values=[float(counts.get((d.isoformat(), status), 0)) for d in days],
        )
        for status in present
    ]
    total = sum(counts.values())
    if not series:
        return ToolResult(summary=f"No seed runs in the last {len(days)} days.")
    spec = ChartSpec(
        chart="bar", labels=[_label(d) for d in days], series=series, stacked=True, unit="runs"
    )
    by_status = {s.name: int(sum(s.values)) for s in series}
    return ToolResult(
        summary=f"{total} seed run(s) in the last {len(days)} days: "
        + ", ".join(f"{n} {name.lower()}" for name, n in by_status.items())
        + ".",
        data={
            "runs_by_status": by_status,
            # Chart-ready: every day (zeros included) and one list of values per outcome.
            "days": spec.labels,
            "runs_per_day": {s.name: [int(v) for v in s.values] for s in series},
        },
        tiles=[chart_tile("seed-history", f"Seed runs per day, last {len(days)} days", spec)],
    )


register(
    ToolSpec(
        name="usage_history",
        description=(
            "Chart the person's own use of the workbench: questions asked per day, tokens by "
            "conversation, and this conversation's token budget."
        ),
        properties={"days": _DAYS_ARG},
        handler=_usage_history,
        category="history",
    )
)
register(
    ToolSpec(
        name="seed_activity",
        description=(
            "Chart the person's seed runs per day by outcome (completed, failed, rolled back)."
        ),
        properties={"days": _DAYS_ARG},
        handler=_seed_activity,
        category="history",
    )
)
