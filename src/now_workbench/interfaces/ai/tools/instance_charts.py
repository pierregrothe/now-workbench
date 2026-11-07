# src/now_workbench/interfaces/ai/tools/instance_charts.py
# Live figures from a ServiceNow instance, drawn as chart tiles (ADR-028).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Instance chart tools: record counts per table, and records created per day.

Figures are read live and read-only from the instance. A count the instance refuses is
reported, never drawn as zero (ADR-013).
"""

import re
from typing import Any

from now_workbench.domains.instances import count_records, daily_created
from now_workbench.interfaces.ai.tools.base import (
    ToolContext,
    ToolResult,
    ToolSpec,
    register,
    resolve_instance,
    run_async,
)
from now_workbench.interfaces.ai.tools.charts import (
    DAYS_ARG,
    ChartSeries,
    ChartSpec,
    chart_tile,
    day_label,
    history_days,
)

__all__: list[str] = []

_TABLE = re.compile(r"^[a-z][a-z0-9_]{0,79}$")
_DEFAULT_TABLES = ["incident", "problem", "change_request", "sc_req_item", "sys_user", "cmdb_ci"]
_INSTANCE_ARG = {
    "type": "string",
    "description": "Instance name or id (default instance if empty).",
}


def _check_tables(tables: list[str]) -> None:
    bad = [t for t in tables if not _TABLE.match(t)]
    if bad:
        raise ValueError(f"Not a table name: {', '.join(bad)}.")


def _record_counts(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    inst = resolve_instance(ctx.conn, args.get("instance"))
    tables = [str(t).strip() for t in args.get("tables") or _DEFAULT_TABLES][:12]
    _check_tables(tables)
    counts = run_async(count_records(inst, tables, fake_mode=ctx.fake_mode))
    read = sorted(((t, n) for t, n in counts.items() if n is not None), key=lambda p: -p[1])
    refused = [t for t, n in counts.items() if n is None]
    if not read:
        return ToolResult(
            summary=f"{inst.name} refused every count: {', '.join(refused)}.", ok=False
        )
    spec = ChartSpec(
        chart="bar",
        labels=[t for t, _ in read],
        series=[ChartSeries(name="Records", values=[float(n) for _, n in read])],
        unit="records",
    )
    note = f" Not readable: {', '.join(refused)}." if refused else ""
    return ToolResult(
        summary=f"Record counts on {inst.name}: "
        + ", ".join(f"{t} {n}" for t, n in read)
        + "."
        + note,
        data={"instance": inst.name, "counts": dict(read), "refused": refused},
        tiles=[chart_tile("instance-counts", f"Records per table on {inst.name}", spec)],
    )


def _records_over_time(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    inst = resolve_instance(ctx.conn, args.get("instance"))
    table = str(args.get("table") or "incident").strip()
    _check_tables([table])
    days = history_days(args)
    counts = run_async(daily_created(inst, table, days, fake_mode=ctx.fake_mode))
    missing = [d for d, n in counts.items() if n is None]
    if missing:
        return ToolResult(
            summary=f"{inst.name} refused the {table} counts for {len(missing)} of "
            f"{len(days)} day(s); nothing is charted rather than guess.",
            ok=False,
        )
    values = [float(counts[d] or 0) for d in days]
    spec = ChartSpec(
        chart="area",
        labels=[day_label(d) for d in days],
        series=[ChartSeries(name=f"New {table}", values=values)],
        unit="records",
    )
    return ToolResult(
        summary=f"{int(sum(values))} {table} record(s) created on {inst.name} in the last "
        f"{len(days)} days.",
        data={
            "instance": inst.name,
            "table": table,
            "days": spec.labels,
            "created_per_day": [int(v) for v in values],
        },
        tiles=[chart_tile("instance-trend", f"New {table} per day on {inst.name}", spec)],
    )


register(
    ToolSpec(
        name="instance_record_counts",
        description=(
            "Chart live record counts per table on a ServiceNow instance (default: incident, "
            "problem, change_request, sc_req_item, sys_user, cmdb_ci). Read-only."
        ),
        properties={
            "instance": _INSTANCE_ARG,
            "tables": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
        },
        handler=_record_counts,
        category="instance",
    )
)
register(
    ToolSpec(
        name="instance_records_over_time",
        description=(
            "Chart how many records of a table were created per day on a ServiceNow instance "
            "(default table: incident). Read-only."
        ),
        properties={"instance": _INSTANCE_ARG, "table": {"type": "string"}, "days": DAYS_ARG},
        handler=_records_over_time,
        category="instance",
    )
)
