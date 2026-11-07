# tests/test_charts.py
# Chart tiles and the history tools that draw the person's own activity (ADR-027).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests for the chart schema, `show` charts and the usage / seed history tools."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from now_workbench.domains.conversations import ChatMessageRecord, ThreadRepository
from now_workbench.domains.identity import AuthUser, Role
from now_workbench.domains.seed import SeedOperationRecord, SeedRepository
from now_workbench.interfaces.ai.tools import REGISTRY, execute_tool
from now_workbench.interfaces.ai.tools.base import ToolContext, ToolResult, register
from now_workbench.interfaces.ai.tools.charts import ChartSeries, ChartSpec, fold_slices
from now_workbench.interfaces.api.app import create_app
from now_workbench.platform.db.session import db_session
from now_workbench.platform.owner import LOCAL_EMAIL, owner_scope

OTHER = "ana@example.com"


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


def _run(tool: str, args: dict[str, Any] | None = None, thread: str = "") -> ToolResult:
    user = AuthUser(email=LOCAL_EMAIL, roles=frozenset(Role), mode="cloudflare")
    with db_session() as conn:
        return execute_tool(ToolContext(conn=conn, user=user, thread_id=thread), tool, args or {})


def _series(*values: float) -> list[ChartSeries]:
    return [ChartSeries(name="s", values=list(values))]


def test_chart_spec_checks_the_shape_of_each_form() -> None:
    """Every form gets data it can draw; a meter needs value and max."""
    assert ChartSpec(chart="line", labels=["a", "b"], series=_series(1, 2)).chart == "line"
    assert ChartSpec(chart="meter", value=3, max=10).max == 10
    bad: list[dict[str, Any]] = [
        {"chart": "meter", "value": 3},
        {"chart": "bar", "labels": ["a"]},
        {"chart": "line", "labels": ["a", "b"], "series": _series(1)},
        {"chart": "pie", "labels": ["a"], "series": _series(-1)},
        {"chart": "donut", "labels": ["a"], "series": _series(1) + _series(2)},
        {"chart": "pie", "labels": list("abcdefghi"), "series": _series(*range(9))},
    ]
    for kwargs in bad:
        with pytest.raises(ValidationError):
            ChartSpec(**kwargs)


def test_fold_slices_keeps_seven_and_folds_the_rest_into_other() -> None:
    """Categorical colors are never cycled, so slice nine and on become 'Other'."""
    labels, values = fold_slices([(f"t{i}", float(i)) for i in range(10)])
    assert labels[0] == "t9" and labels[-1] == "Other" and len(labels) == 8
    assert values[-1] == 0 + 1 + 2
    assert fold_slices([("a", 1.0), ("b", 2.0)]) == (["b", "a"], [2.0, 1.0])


def test_show_draws_charts_and_kpi_trends(client: TestClient) -> None:
    """Otto's chart and trend arrive as tiles; a malformed chart shows nothing."""
    res = _run(
        "show",
        {
            "tiles": [
                {
                    "kind": "chart",
                    "title": "Mix",
                    "chart": "donut",
                    "labels": ["a", "b"],
                    "series": [{"name": "n", "values": [1, 3]}],
                    "span": 1,
                },
                {"kind": "kpis", "items": [{"label": "Runs", "value": 4, "trend": [1, 2, 4]}]},
            ]
        },
    )
    assert res.ok and [t.type for t in res.tiles] == ["chart", "kpis"]
    assert res.tiles[0].span == 1 and res.tiles[0].props["series"][0]["values"] == [1.0, 3.0]
    assert res.tiles[1].props["items"][0]["trend"] == [1.0, 2.0, 4.0]
    assert res.tiles[1].props["items"][0]["value"] == "4"
    wrong = {"kind": "chart", "chart": "line", "labels": ["a"], "series": []}
    assert not _run("show", {"tiles": [wrong]}).ok


def test_usage_history_charts_questions_tokens_and_the_budget(client: TestClient) -> None:
    """Questions per day are counted, missing days are zero, and only the owner's data shows."""
    thread = client.post("/api/threads", json={"title": "Busy"}).json()["id"]
    now = datetime.now(UTC)
    with db_session() as conn:
        repo = ThreadRepository(conn)
        for i, when in enumerate([now, now, now - timedelta(days=2), now - timedelta(days=90)]):
            repo.add_message(
                ChatMessageRecord(
                    id=f"q{i}", thread_id=thread, role="user", content="?", created_at=when
                )
            )
        repo.add_message(
            ChatMessageRecord(id="a0", thread_id=thread, role="assistant", content="!")
        )
        repo.add_thread_tokens(thread, 1500)
    res = _run("usage_history", {"days": 7}, thread=thread)
    assert res.ok and "3 question(s) in the last 7 days" in res.summary
    per_day = res.data["questions_per_day"]
    assert len(per_day) == 7 and per_day[now.date().isoformat()] == 2
    assert per_day[(now - timedelta(days=1)).date().isoformat()] == 0
    charts = {t.id: t.props for t in res.tiles}
    assert charts["usage-questions"]["chart"] == "area"
    assert charts["usage-tokens"]["labels"] == ["Busy"]
    assert charts["usage-limit"]["value"] == 1500
    with db_session() as conn, owner_scope(OTHER):
        assert ThreadRepository(conn).daily_question_counts("2000-01-01") == {}


def test_usage_history_without_activity_shows_an_empty_series(client: TestClient) -> None:
    """No questions and no tokens: one chart of zeros, no donut and no budget meter."""
    res = _run("usage_history", {"days": 200})
    assert res.ok and len(res.data["questions_per_day"]) == 60
    assert [t.id for t in res.tiles] == ["usage-questions"]


def test_seed_activity_stacks_runs_by_outcome(client: TestClient) -> None:
    """Statuses keep a fixed order; unknown statuses follow; no runs is said plainly."""
    assert "No seed runs" in _run("seed_activity").summary
    with db_session() as conn:
        repo = SeedRepository(conn)
        for i, status in enumerate(["failed", "completed", "completed", "paused"]):
            repo.record_seed_operation(
                SeedOperationRecord(
                    id=f"op{i}",
                    bundle_id="b",
                    instance_id="i",
                    status=status,
                    created_records=[],
                )
            )
    res = _run("seed_activity", {"days": 3})
    spec = res.tiles[0].props
    assert spec["chart"] == "bar" and spec["stacked"] and len(spec["labels"]) == 3
    assert [s["name"] for s in spec["series"]] == ["Completed", "Failed", "Paused"]
    assert res.data["runs_by_status"] == {"Completed": 2, "Failed": 1, "Paused": 1}
    assert len(res.data["days"]) == 3
    assert res.data["runs_per_day"] == {
        "Completed": [0, 0, 2],
        "Failed": [0, 0, 1],
        "Paused": [0, 0, 1],
    }
    assert "4 seed run(s)" in res.summary


def test_register_refuses_a_duplicate_tool_name() -> None:
    """A second tool with a taken name fails loudly instead of replacing the first."""
    with pytest.raises(ValueError, match="already registered"):
        register(REGISTRY["show"])
