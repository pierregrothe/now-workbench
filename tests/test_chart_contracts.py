# tests/test_chart_contracts.py
# Exact results of the chart and telemetry tools: every tile, summary and figure (ADR-027/028).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Contract tests: the whole result of each history and instance tool, compared exactly.

They pin what a person and Otto receive, so a change to any title, unit, series, figure or
argument fails here; they are what kills the mutants the field-level tests let through.
"""

import asyncio
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from now_workbench.domains.conversations import (
    ChatMessageRecord,
    ChatThreadCreate,
    ThreadRepository,
)
from now_workbench.domains.identity import AuthUser, Role
from now_workbench.domains.instances import (
    InstanceCreate,
    InstanceRecord,
    InstanceRepository,
    count_records,
    daily_created,
)
from now_workbench.domains.seed import SeedOperationRecord, SeedRepository
from now_workbench.domains.telemetry import TelemetryRepository, record_action, record_usage
from now_workbench.interfaces.ai.tools import execute_tool, instance_charts
from now_workbench.interfaces.ai.tools.base import ToolContext, ToolResult
from now_workbench.interfaces.ai.tools.charts import daily_series, fold_slices, history_days
from now_workbench.interfaces.api.app import create_app
from now_workbench.platform.db.session import db_session
from now_workbench.platform.owner import LOCAL_EMAIL, owner_scope

ANA = "ana@example.com"
ADMIN = AuthUser(email=LOCAL_EMAIL, roles=frozenset(Role), mode="cloudflare")
ANA_USER = AuthUser(email=ANA, roles=frozenset({Role.SOLUTION_CONSULTANT}), mode="cloudflare")


@pytest.fixture(autouse=True)
def _db() -> None:
    TestClient(create_app())


def _days(n: int) -> list[date]:
    today = datetime.now(UTC).date()
    return [today - timedelta(days=i) for i in range(n - 1, -1, -1)]


def _labels(n: int) -> list[str]:
    return [d.strftime("%b %d") for d in _days(n)]


def _run(tool: str, args: dict[str, Any] | None = None, **ctx: Any) -> ToolResult:
    user = ctx.pop("user", ADMIN)
    with db_session() as conn:
        return execute_tool(ToolContext(conn=conn, user=user, **ctx), tool, args or {})


def _chart(tile_id: str, title: str, span: int | None = None, **spec: Any) -> dict[str, Any]:
    props = {
        "chart": spec.pop("chart"),
        "labels": spec.pop("labels", []),
        "series": spec.pop("series", []),
        "unit": spec.pop("unit", ""),
        "stacked": spec.pop("stacked", False),
        "value": spec.pop("value", None),
        "max": spec.pop("max", None),
    }
    assert not spec
    return {"id": tile_id, "type": "chart", "title": title, "props": props, "span": span}


def _result(summary: str, data: dict[str, Any], tiles: list[Any], layout: str = "1-col") -> Any:
    return {
        "summary": summary,
        "ok": True,
        "pending": False,
        "data": data,
        "tiles": tiles,
        "layout": layout,
        "images": [],
        "shown": False,
        "ui": [],
    }


def _event(table: str, day: date, **cols: Any) -> None:
    """Insert a telemetry row on a given day (the recorders always stamp now)."""
    names = ", ".join([*cols, "created_at"])
    marks = ", ".join("?" * (len(cols) + 1))
    with db_session() as conn, conn:
        conn.execute(
            f"INSERT INTO {table} ({names}) VALUES ({marks})",
            (*cols.values(), f"{day.isoformat()}T12:00:00.000Z"),
        )


# --- chart helpers -------------------------------------------------------------------------------


def test_fold_slices_ranks_by_value_and_folds_only_past_eight() -> None:
    """Order is by value, not label; exactly eight slices stay as they are."""
    assert fold_slices([("a", 2.0), ("z", 1.0)]) == (["a", "z"], [2.0, 1.0])
    eight = [(f"s{i}", float(i)) for i in range(8)]
    labels, _ = fold_slices(eight)
    assert len(labels) == 8 and "Other" not in labels


def test_history_days_defaults_to_thirty_and_clamps() -> None:
    """No `days` means 30; the range is clamped to 1..60 and ends today."""
    assert history_days({}) == _days(30)
    assert history_days({"days": 0}) == _days(30)
    assert history_days({"days": -5}) == _days(1)
    assert history_days({"days": 99}) == _days(60)


def test_daily_series_names_unknown_keys_readably() -> None:
    """A key outside the known order keeps a readable name: underscores become spaces."""
    days = _days(1)
    series = daily_series(days, {(days[0].isoformat(), "paused_by_admin"): 2}, {})
    assert [(s.name, s.values) for s in series] == [("Paused by admin", [2.0])]


# --- usage, actions, seed runs, team -----------------------------------------------------------


def test_usage_history_returns_exactly_these_tiles_and_figures() -> None:
    """Questions, tokens per day, the share per conversation and this one's budget."""
    title = "A conversation title that is longer than forty characters"
    with db_session() as conn:
        repo = ThreadRepository(conn)
        thread = repo.create_thread(ChatThreadCreate(title=title)).id
        repo.add_message(ChatMessageRecord(id="q1", thread_id=thread, role="user", content="?"))
        repo.add_thread_tokens(thread, 1500)
        record_usage(
            conn, ADMIN, "m", {"input": 10, "output": 2, "cache_write": 3, "cache_read": 4}
        )
    res = _run("usage_history", {"days": 2}, thread_id=thread)
    labels = _labels(2)
    assert res.model_dump() == _result(
        "1 question(s) in the last 2 days; 1500 billable tokens across 1 conversation(s). "
        "Conversation totals are billable tokens (input + output + 1.25 x cache writes + 0.1 x "
        "cache reads); tokens per day are raw counts by kind, so they add up to more.",
        {
            "questions_per_day": {d.isoformat(): n for d, n in zip(_days(2), [0, 1], strict=True)},
            "tokens_per_day": {
                "days": labels,
                "per_day": {
                    "Input": [0, 10],
                    "Output": [0, 2],
                    "Cache write": [0, 3],
                    "Cache read": [0, 4],
                },
            },
            "billable_tokens_by_conversation": {title[:40]: 1500.0},
        },
        [
            _chart(
                "usage-questions",
                "Questions per day, last 2 days",
                chart="area",
                labels=labels,
                series=[{"name": "Questions", "values": [0.0, 1.0]}],
            ),
            _chart(
                "usage-tokens-daily",
                "Tokens per day",
                chart="bar",
                stacked=True,
                unit="tokens",
                labels=labels,
                series=[
                    {"name": "Input", "values": [0.0, 10.0]},
                    {"name": "Output", "values": [0.0, 2.0]},
                    {"name": "Cache write", "values": [0.0, 3.0]},
                    {"name": "Cache read", "values": [0.0, 4.0]},
                ],
            ),
            _chart(
                "usage-tokens",
                "Billable tokens by conversation",
                span=1,
                chart="donut",
                unit="tokens",
                labels=[title[:40]],
                series=[{"name": "Tokens", "values": [1500.0]}],
            ),
            _chart(
                "usage-limit",
                "This conversation's budget (billable tokens)",
                span=1,
                chart="meter",
                unit="tokens",
                value=1500.0,
                max=2000000.0,
            ),
        ],
        layout="2-col",
    )


def test_usage_history_names_an_untitled_conversation() -> None:
    """A conversation without a title is shown as 'Untitled', not as an empty slice."""
    with db_session() as conn:
        conn.execute(
            "INSERT INTO chat_threads (id, title, owner_email, tokens_used) VALUES ('t', '', ?, 5)",
            (LOCAL_EMAIL,),
        )
        conn.commit()
    assert _run("usage_history", {"days": 1}).data["billable_tokens_by_conversation"] == {
        "Untitled": 5.0
    }


def test_action_history_returns_exactly_these_tiles_and_figures() -> None:
    """Runs per day by outcome from the first day on, and the eight most used actions."""
    days = _days(3)
    _event(
        "action_events",
        days[0],
        owner_email=LOCAL_EMAIL,
        actor_email=LOCAL_EMAIL,
        name="a0",
        source="otto",
        outcome="failed",
        duration_ms=40,
    )
    for i in range(1, 9):
        _event(
            "action_events",
            days[2],
            owner_email=LOCAL_EMAIL,
            actor_email=LOCAL_EMAIL,
            name=f"a{i}",
            source="actions",
            outcome="ok",
            duration_ms=10 * i,
        )
    _event(
        "action_events",
        days[2],
        owner_email=LOCAL_EMAIL,
        actor_email=LOCAL_EMAIL,
        name="a1",
        source="otto",
        outcome="pending",
        duration_ms=0,
    )
    res = _run("action_history", {"days": 3})
    labels = _labels(3)
    totals = [{"name": "a1", "runs": 2, "failed": 0, "avg_ms": 5}] + [
        {"name": f"a{i}", "runs": 1, "failed": int(i == 0), "avg_ms": 40 if i == 0 else 10 * i}
        for i in (0, 2, 3, 4, 5, 6, 7, 8)
    ]
    assert res.model_dump() == _result(
        "10 action run(s) in the last 3 days, 1 failed.",
        {
            "actions": totals,
            "days": labels,
            "per_day": {
                "Succeeded": [0, 0, 8],
                "Failed": [1, 0, 0],
                "Awaiting confirmation": [0, 0, 1],
            },
        },
        [
            _chart(
                "actions-daily",
                "Actions per day",
                chart="bar",
                stacked=True,
                unit="runs",
                labels=labels,
                series=[
                    {"name": "Succeeded", "values": [0.0, 0.0, 8.0]},
                    {"name": "Failed", "values": [1.0, 0.0, 0.0]},
                    {"name": "Awaiting confirmation", "values": [0.0, 0.0, 1.0]},
                ],
            ),
            _chart(
                "actions-top",
                "Most used actions",
                chart="bar",
                unit="runs",
                labels=[t["name"] for t in totals[:8]],
                series=[{"name": "Runs", "values": [2.0] + [1.0] * 7}],
            ),
        ],
        layout="2-col",
    )


def test_seed_activity_returns_exactly_this_chart() -> None:
    """Seed runs per day from the first day on, stacked by outcome, summarised in words."""
    yesterday = datetime.now(UTC) - timedelta(days=1)
    with db_session() as conn:
        repo = SeedRepository(conn)
        repo.record_seed_operation(
            SeedOperationRecord(
                id="o0",
                bundle_id="b",
                instance_id="i",
                status="completed",
                created_records=[],
                created_at=yesterday.isoformat(),
            )
        )
        repo.record_seed_operation(
            SeedOperationRecord(
                id="o1", bundle_id="b", instance_id="i", status="failed", created_records=[]
            )
        )
    res = _run("seed_activity", {"days": 2})
    labels = _labels(2)
    assert res.model_dump() == _result(
        "2 seed run(s) in the last 2 days: 1 completed, 1 failed.",
        {
            "runs_by_status": {"Completed": 1, "Failed": 1},
            "days": labels,
            "per_day": {"Completed": [1, 0], "Failed": [0, 1]},
        },
        [
            _chart(
                "seed-history",
                "Seed runs per day, last 2 days",
                chart="bar",
                stacked=True,
                unit="runs",
                labels=labels,
                series=[
                    {"name": "Completed", "values": [1.0, 0.0]},
                    {"name": "Failed", "values": [0.0, 1.0]},
                ],
            )
        ],
    )


def test_team_usage_returns_exactly_these_tiles_and_figures() -> None:
    """The team's tokens per day include everyone; tokens and runs are charted per person."""
    with db_session() as conn:
        record_usage(conn, ADMIN, "m", {"input": 1, "output": 2, "cache_write": 3, "cache_read": 4})
        with owner_scope(ANA):
            record_usage(conn, ANA_USER, "m", {"input": 5})
            record_action(conn, ANA_USER, "list_instances", "otto", "ok", 3)
    res = _run("team_usage", {"days": 1})
    labels = _labels(1)
    assert res.model_dump() == _result(
        "Last 1 days: 15 tokens and 1 action run(s) across 2 person(s).",
        {
            "tokens_by_person": {LOCAL_EMAIL: 10, ANA: 5},
            "actions_by_person": {ANA: 1},
            "tokens": {
                "days": labels,
                "per_day": {"Input": [6], "Output": [2], "Cache write": [3], "Cache read": [4]},
            },
        },
        [
            _chart(
                "team-tokens-daily",
                "Team tokens per day",
                chart="bar",
                stacked=True,
                unit="tokens",
                labels=labels,
                series=[
                    {"name": "Input", "values": [6.0]},
                    {"name": "Output", "values": [2.0]},
                    {"name": "Cache write", "values": [3.0]},
                    {"name": "Cache read", "values": [4.0]},
                ],
            ),
            _chart(
                "team-tokens",
                "Tokens by person",
                chart="bar",
                unit="tokens",
                labels=[LOCAL_EMAIL, ANA],
                series=[{"name": "tokens", "values": [10.0, 5.0]}],
            ),
            _chart(
                "team-actions",
                "Actions by person",
                chart="bar",
                unit="runs",
                labels=[ANA],
                series=[{"name": "runs", "values": [1.0]}],
            ),
        ],
        layout="2-col",
    )


# --- telemetry records ---------------------------------------------------------------------------


def test_record_action_and_usage_store_every_field_as_given() -> None:
    """Zero and negative durations, a missing conversation, and the real actor under view-as."""
    viewing = AuthUser(
        email=ANA,
        roles=frozenset({Role.SOLUTION_CONSULTANT}),
        mode="cloudflare",
        real_email=LOCAL_EMAIL,
        real_roles=frozenset(Role),
    )
    with db_session() as conn, owner_scope(ANA):
        record_action(conn, viewing, "x", "otto", "ok", 0)
        record_action(conn, None, "y", "actions", "failed", -7)
        record_usage(conn, viewing, "model-a", {"input": 1})
        actions = conn.execute(
            "SELECT owner_email, actor_email, name, source, outcome, duration_ms "
            "FROM action_events ORDER BY id"
        ).fetchall()
        usage = conn.execute(
            "SELECT owner_email, actor_email, thread_id, model FROM usage_events"
        ).fetchall()
    assert [tuple(r) for r in actions] == [
        (ANA, LOCAL_EMAIL, "x", "otto", "ok", 0),
        (ANA, ANA, "y", "actions", "failed", 0),
    ]
    assert [tuple(r) for r in usage] == [(ANA, LOCAL_EMAIL, "", "model-a")]


def test_telemetry_reads_default_to_the_owner_only() -> None:
    """Without `everyone`, aggregates leave out other people's runs."""
    with db_session() as conn:
        with owner_scope(ANA):
            record_action(conn, ANA_USER, "theirs", "otto", "ok", 1)
        record_action(conn, ADMIN, "mine", "otto", "ok", 1)
        repo = TelemetryRepository(conn)
        today = _days(1)[0].isoformat()
        assert repo.daily_actions(today) == {(today, "ok"): 1}
        assert [t["name"] for t in repo.action_totals(today)] == ["mine"]


# --- live instance figures -----------------------------------------------------------------------


def _counting(counts: dict[str, Any], seen: list[httpx.Request]) -> httpx.MockTransport:
    def handle(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        value = counts.get(req.url.path.rsplit("/", 1)[-1], 1)
        if isinstance(value, httpx.Response):
            return value
        return httpx.Response(200, json={"result": {"stats": {"count": str(value)}}})

    return httpx.MockTransport(handle)


def test_count_records_follows_redirects_and_sends_no_password_without_basic_auth() -> None:
    """A redirected stats call is followed; an OAuth-style instance sends no Basic header."""
    seen: list[httpx.Request] = []

    def handle(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        if req.url.path.startswith("/old/"):
            return httpx.Response(200, json={"result": {"stats": {"count": "3"}}})
        return httpx.Response(302, headers={"Location": "https://acme.service-now.com/old/x"})

    inst = InstanceRecord(
        id="i", name="Acme", url="https://acme.service-now.com/", auth_type="oauth"
    )
    counts = asyncio.run(count_records(inst, ["incident"], transport=httpx.MockTransport(handle)))
    assert counts == {"incident": 3}
    assert str(seen[0].url).startswith("https://acme.service-now.com/api/now/stats/incident?")
    assert seen[0].extensions["timeout"] == {
        "connect": 15.0,
        "read": 15.0,
        "write": 15.0,
        "pool": 15.0,
    }
    assert "authorization" not in seen[0].headers


def test_daily_created_refuses_in_fake_mode() -> None:
    """The workbench's own fake mode refuses live figures too."""
    inst = InstanceRecord(id="i", name="Acme", url="https://acme.service-now.com")
    with pytest.raises(ValueError, match="simulated"):
        asyncio.run(count_records(inst, ["incident"], fake_mode=True))


@pytest.fixture
def two_instances(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[dict[str, Any]], list[httpx.Request]]:
    """Alpha (default) and Beta, with the tools' HTTP routed to a fake ServiceNow."""
    with db_session() as conn:
        repo = InstanceRepository(conn)
        repo.add_instance(
            InstanceCreate(name="Alpha", url="https://alpha.service-now.com", is_default=True)
        )
        repo.add_instance(InstanceCreate(name="Beta", url="https://beta.service-now.com"))

    def use(counts: dict[str, Any]) -> list[httpx.Request]:
        seen: list[httpx.Request] = []
        transport = _counting(counts, seen)

        async def counted(inst: InstanceRecord, tables: list[str], fake_mode: bool = False) -> Any:
            return await count_records(inst, tables, fake_mode, transport)

        async def daily(
            inst: InstanceRecord, table: str, days: list[date], fake_mode: bool = False
        ) -> Any:
            return await daily_created(inst, table, days, fake_mode, transport)

        monkeypatch.setattr(instance_charts, "count_records", counted)
        monkeypatch.setattr(instance_charts, "daily_created", daily)
        return seen

    return use


def test_instance_record_counts_returns_exactly_this_chart(two_instances: Any) -> None:
    """The named instance is counted, at most twelve tables, largest first, no refusal note."""
    seen = two_instances({"t0": 50, "t1": 7})
    tables = [f"t{i}" for i in range(13)]
    res = _run("instance_record_counts", {"instance": "Beta", "tables": tables})
    counted = [f"t{i}" for i in range(12)]
    order = ["t0", "t1", *sorted(set(counted) - {"t0", "t1"}, key=counted.index)]
    values = [50.0, 7.0] + [1.0] * 10
    assert res.model_dump() == _result(
        "Record counts on Beta: "
        + ", ".join(f"{t} {int(v)}" for t, v in zip(order, values, strict=True))
        + ".",
        {
            "instance": "Beta",
            "counts": dict(zip(order, [int(v) for v in values], strict=True)),
            "refused": [],
        },
        [
            _chart(
                "instance-counts",
                "Records per table on Beta",
                chart="bar",
                unit="records",
                labels=order,
                series=[{"name": "Records", "values": values}],
            )
        ],
    )
    assert {r.url.host for r in seen} == {"beta.service-now.com"} and len(seen) == 12


def test_instance_record_counts_passes_fake_mode_through(two_instances: Any) -> None:
    """In fake mode the live tools refuse instead of contacting the instance."""
    two_instances({})
    res = _run("instance_record_counts", fake_mode=True)
    assert not res.ok and "simulated" in res.summary
    assert not _run("instance_records_over_time", fake_mode=True).ok


def test_instance_records_over_time_returns_exactly_this_chart(two_instances: Any) -> None:
    """Default table incident and 30 days; a day with no records is a real zero."""
    seen = two_instances({"incident": 0})
    res = _run("instance_records_over_time", {"instance": "Beta"})
    labels = _labels(30)
    assert res.model_dump() == _result(
        "0 incident record(s) created on Beta in the last 30 days.",
        {"instance": "Beta", "table": "incident", "days": labels, "created_per_day": [0] * 30},
        [
            _chart(
                "instance-trend",
                "New incident per day on Beta",
                chart="area",
                unit="records",
                labels=labels,
                series=[{"name": "New incident", "values": [0.0] * 30}],
            )
        ],
    )
    assert {r.url.host for r in seen} == {"beta.service-now.com"}


def test_instance_chart_tools_name_every_bad_table(two_instances: Any) -> None:
    """All rejected names are listed, separated by commas."""
    two_instances({})
    res = _run("instance_record_counts", {"tables": ["A b", "c/d"]})
    assert res.summary == "instance_record_counts failed: Not a table name: A b, c/d."


def test_instance_record_counts_lists_every_refused_table(two_instances: Any) -> None:
    """Several refused tables are named in the summary, separated by commas."""
    two_instances({"a": httpx.Response(403), "b": httpx.Response(403), "c": 4})
    res = _run("instance_record_counts", {"tables": ["a", "b", "c"]})
    assert res.summary == "Record counts on Alpha: c 4. Not readable: a, b."
