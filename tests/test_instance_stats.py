# tests/test_instance_stats.py
# Live instance figures: Aggregate API counts, refusals kept apart from zeros (ADR-028).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests for instance record counts and records-per-day, and the tools that chart them."""

import asyncio
from collections.abc import Callable
from datetime import date
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from now_workbench.domains.identity import AuthUser, Role
from now_workbench.domains.instances import (
    InstanceCreate,
    InstanceRecord,
    InstanceRepository,
    count_records,
    daily_created,
)
from now_workbench.interfaces.ai.tools import execute_tool, instance_charts
from now_workbench.interfaces.ai.tools.base import ToolContext, ToolResult
from now_workbench.interfaces.api.app import create_app
from now_workbench.platform.db.session import db_session
from now_workbench.platform.owner import LOCAL_EMAIL

Handler = Callable[[httpx.Request], httpx.Response]


def _inst(url: str = "https://acme.service-now.com") -> InstanceRecord:
    return InstanceRecord(id="i1", name="Acme", url=url, username="admin", password="pw")


def _servicenow(counts: dict[str, Any], seen: list[httpx.Request] | None = None) -> Handler:
    """A fake Aggregate API: a count per table, an HTTP status, or a raised network error."""

    def handle(req: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(req)
        table = req.url.path.rsplit("/", 1)[-1]
        value = counts[table]
        if isinstance(value, Exception):
            raise value
        if isinstance(value, httpx.Response):
            return value
        if callable(value):
            return value(req)
        return httpx.Response(200, json={"result": {"stats": {"count": str(value)}}})

    return handle


def test_count_records_keeps_refusals_apart_from_zero() -> None:
    """A count is a number; a refusal, a failure or a bad payload is None, never 0."""
    seen: list[httpx.Request] = []
    handler = _servicenow(
        {
            "incident": 42,
            "problem": 0,
            "secret": httpx.Response(403),
            "broken": httpx.Response(200, json={"result": {}}),
            "garbled": httpx.Response(200, text="<html>"),
            "down": httpx.ConnectError("no route"),
        },
        seen,
    )
    tables = ["incident", "problem", "secret", "broken", "garbled", "down"]
    counts = asyncio.run(count_records(_inst(), tables, transport=httpx.MockTransport(handler)))
    assert counts == {
        "incident": 42,
        "problem": 0,
        "secret": None,
        "broken": None,
        "garbled": None,
        "down": None,
    }
    first = seen[0]
    assert str(first.url).startswith("https://acme.service-now.com/api/now/stats/")
    assert first.url.params["sysparm_count"] == "true" and "sysparm_query" not in first.url.params
    assert first.headers["authorization"].startswith("Basic ")
    assert first.headers["accept"] == "application/json"


def test_daily_created_queries_each_day_between_midnights() -> None:
    """One count per day, bounded from that midnight to the next."""
    seen: list[httpx.Request] = []

    def per_day(req: httpx.Request) -> httpx.Response:
        n = 5 if "2026-11-06 00:00:00^" in req.url.params["sysparm_query"] else 1
        return httpx.Response(200, json={"result": {"stats": {"count": str(n)}}})

    days = [date(2026, 11, 5), date(2026, 11, 6)]
    transport = httpx.MockTransport(_servicenow({"incident": per_day}, seen))
    counts = asyncio.run(daily_created(_inst(), "incident", days, transport=transport))
    assert counts == {date(2026, 11, 5): 1, date(2026, 11, 6): 5}
    queries = sorted(r.url.params["sysparm_query"] for r in seen)
    assert queries[0] == ("sys_created_on>=2026-11-05 00:00:00^sys_created_on<2026-11-06 00:00:00")


def test_instance_stats_refuse_a_simulated_instance_or_workbench() -> None:
    """No figures are invented: a fake instance or fake mode is an error, not zeros."""
    with pytest.raises(ValueError, match="simulated"):
        asyncio.run(count_records(_inst("fake://acme"), ["incident"]))
    with pytest.raises(ValueError, match="simulated"):
        asyncio.run(daily_created(_inst(), "incident", [date(2026, 11, 5)], fake_mode=True))


# --- the tools ---------------------------------------------------------------------------------


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[str, Any]], None]:
    """Register a real-looking instance and route the tools' HTTP to a fake ServiceNow."""
    TestClient(create_app())
    with db_session() as conn:
        InstanceRepository(conn).add_instance(
            InstanceCreate(
                name="Acme",
                url="https://acme.service-now.com",
                username="admin",
                password="pw",
                is_default=True,
            )
        )

    def use(counts: dict[str, Any]) -> None:
        transport = httpx.MockTransport(_servicenow(counts))

        async def counted(inst: InstanceRecord, tables: list[str], fake_mode: bool = False) -> Any:
            return await count_records(inst, tables, fake_mode, transport)

        async def daily(
            inst: InstanceRecord, table: str, days: list[date], fake_mode: bool = False
        ) -> Any:
            return await daily_created(inst, table, days, fake_mode, transport)

        monkeypatch.setattr(instance_charts, "count_records", counted)
        monkeypatch.setattr(instance_charts, "daily_created", daily)

    return use


def _run(tool: str, args: dict[str, Any] | None = None) -> ToolResult:
    user = AuthUser(email=LOCAL_EMAIL, roles=frozenset(Role), mode="cloudflare")
    with db_session() as conn:
        return execute_tool(ToolContext(conn=conn, user=user), tool, args or {})


def test_instance_record_counts_charts_counts_and_names_refusals(live: Any) -> None:
    """Tables are drawn largest first; a refused table is named, not drawn as zero."""
    live({"incident": 7, "problem": 30, "secret": httpx.Response(403)})
    res = _run("instance_record_counts", {"tables": ["incident", "problem", "secret"]})
    spec = res.tiles[0].props
    assert spec["labels"] == ["problem", "incident"]
    assert spec["series"][0]["values"] == [30.0, 7.0]
    assert res.summary == "Record counts on Acme: problem 30, incident 7. Not readable: secret."
    assert res.data["refused"] == ["secret"]


def test_instance_record_counts_uses_the_default_tables(live: Any) -> None:
    """Without tables, six common ones are counted; all refused is a failure."""
    live({t: httpx.Response(403) for t in instance_charts._DEFAULT_TABLES})
    res = _run("instance_record_counts")
    assert not res.ok and "refused every count" in res.summary
    assert "incident, problem, change_request, sc_req_item, sys_user, cmdb_ci" in res.summary


def test_instance_records_over_time_charts_each_day_or_nothing(live: Any) -> None:
    """Every day counted is charted; one refused day means no chart rather than a guess."""
    live({"incident": 2})
    res = _run("instance_records_over_time", {"days": 3})
    assert res.ok and res.data["created_per_day"] == [2, 2, 2]
    assert res.summary == "6 incident record(s) created on Acme in the last 3 days."
    assert res.tiles[0].props["chart"] == "area"
    live({"change_request": httpx.Response(500)})
    bad = _run("instance_records_over_time", {"table": "change_request", "days": 2})
    assert not bad.ok and "refused the change_request counts for 2 of 2 day(s)" in bad.summary


def test_instance_chart_tools_reject_a_table_name_that_is_not_one(live: Any) -> None:
    """Table names go into the URL path, so only plain names are accepted."""
    live({})
    res = _run("instance_records_over_time", {"table": "../stats/x"})
    assert not res.ok and "Not a table name: ../stats/x" in res.summary
    assert not _run("instance_record_counts", {"tables": ["ok", "Bad Name"]}).ok
