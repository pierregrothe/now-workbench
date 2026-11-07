# tests/test_telemetry.py
# Telemetry is recorded at its choke points, cannot be bypassed, and feeds the charts (ADR-028).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests for usage and action telemetry, its enforcement guards, and the charts it feeds."""

import logging
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from now_workbench.domains.identity import AuthUser, Role
from now_workbench.domains.telemetry import TelemetryRepository, record_usage
from now_workbench.interfaces.ai.agent import stream_usage_recorder
from now_workbench.interfaces.ai.tools import execute_tool
from now_workbench.interfaces.ai.tools.base import ToolContext, ToolResult
from now_workbench.interfaces.api import replies as replies_api
from now_workbench.interfaces.api.app import create_app
from now_workbench.platform.config.settings import settings
from now_workbench.platform.db.session import db_session
from now_workbench.platform.owner import LOCAL_EMAIL, owner_scope

SRC = Path(__file__).resolve().parents[1] / "src" / "now_workbench"
ANA = "ana@example.com"
ADMIN_USER = AuthUser(email=LOCAL_EMAIL, roles=frozenset(Role), mode="cloudflare")
ANA_USER = AuthUser(email=ANA, roles=frozenset({Role.SOLUTION_CONSULTANT}), mode="cloudflare")


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _actions() -> list[sqlite3.Row]:
    with db_session() as conn:
        return conn.execute(
            "SELECT owner_email, actor_email, name, source, outcome, duration_ms "
            "FROM action_events ORDER BY id"
        ).fetchall()


def _usage() -> list[sqlite3.Row]:
    with db_session() as conn:
        return conn.execute(
            "SELECT owner_email, actor_email, thread_id, model, input_tokens, output_tokens, "
            "cache_write, cache_read FROM usage_events ORDER BY id"
        ).fetchall()


def _run(tool: str, args: dict[str, Any] | None = None, **ctx: Any) -> ToolResult:
    user = ctx.pop("user", ADMIN_USER)
    with db_session() as conn:
        return execute_tool(ToolContext(conn=conn, user=user, **ctx), tool, args or {})


# --- recording at the choke points -----------------------------------------------------------


def test_execute_tool_records_each_outcome_and_who_started_it(client: TestClient) -> None:
    """ok, failed and pending runs are recorded with their source; unknown tools are not."""
    assert _run("list_instances").ok
    assert not _run("show", {"tiles": []}).ok
    assert _run("reset_settings", source="actions").pending
    assert not _run("no_such_tool").ok
    rows = [tuple(r)[:5] for r in _actions()]
    assert rows == [
        (LOCAL_EMAIL, LOCAL_EMAIL, "list_instances", "otto", "ok"),
        (LOCAL_EMAIL, LOCAL_EMAIL, "show", "otto", "failed"),
        (LOCAL_EMAIL, LOCAL_EMAIL, "reset_settings", "actions", "pending"),
    ]
    assert all(r["duration_ms"] >= 0 for r in _actions())


def test_execute_tool_records_the_real_administrator_behind_view_as(client: TestClient) -> None:
    """Under "view as", the data is the person's but the actor is the administrator."""
    viewing = AuthUser(
        email=ANA,
        roles=frozenset({Role.SOLUTION_CONSULTANT}),
        mode="cloudflare",
        real_email=LOCAL_EMAIL,
        real_roles=frozenset(Role),
    )
    with owner_scope(ANA):
        _run("list_instances", user=viewing)
    assert tuple(_actions()[0])[:2] == (ANA, LOCAL_EMAIL)


def test_execute_tool_keeps_the_result_when_telemetry_cannot_be_written(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """A failed telemetry write is logged loudly and never undoes or hides the action."""
    with db_session() as conn:
        conn.execute("DROP TABLE action_events")
        with caplog.at_level(logging.ERROR):
            res = execute_tool(ToolContext(conn=conn, user=ADMIN_USER), "list_instances", {})
    assert res.ok
    assert "Could not record the run of 'list_instances'" in caplog.text


@dataclass
class _Block:
    type: str
    text: str = ""
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class _Resp:
    content: list[Any]
    stop_reason: str = "end_turn"
    usage: Any = field(
        default_factory=lambda: SimpleNamespace(
            input_tokens=11,
            output_tokens=7,
            cache_creation_input_tokens=5,
            cache_read_input_tokens=3,
        )
    )


class _Scripted:
    def __init__(self, script: list[_Resp]) -> None:
        self.messages = SimpleNamespace(create=lambda **_kw: script.pop(0))


def test_post_thread_message_records_every_claude_call(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each call in Otto's tool loop is one usage record, tied to the conversation."""
    script = [
        _Resp(
            [_Block("tool_use", id="t1", name="list_instances")],
            stop_reason="tool_use",
        ),
        _Resp([_Block("text", text="Done.")]),
    ]
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test-0000")
    monkeypatch.setattr(replies_api, "make_client", lambda _key: _Scripted(script))
    thread = client.post("/api/threads", json={"title": "t"}).json()["id"]
    client.post(f"/api/threads/{thread}/messages", json={"content": "list them"})
    rows = [tuple(r) for r in _usage()]
    assert len(rows) == 2
    assert rows[0] == (LOCAL_EMAIL, LOCAL_EMAIL, thread, rows[0][3], 11, 7, 5, 3)
    assert rows[0][3] == rows[1][3] != ""
    assert [r["name"] for r in _actions()] == ["list_instances"]


def test_stream_usage_recorder_records_a_stream_and_skips_one_without_usage(
    client: TestClient,
) -> None:
    """The legacy streaming path records its tokens too; a message without usage adds nothing."""
    record = stream_usage_recorder("m-1", "th-1")
    record(_Resp([], usage=SimpleNamespace(input_tokens=4, output_tokens=2)))
    record(SimpleNamespace())
    assert [tuple(r) for r in _usage()] == [(LOCAL_EMAIL, LOCAL_EMAIL, "th-1", "m-1", 4, 2, 0, 0)]


# --- enforcement: nothing runs a tool or calls Claude around the recorders ---------------------


def _sources() -> dict[str, str]:
    return {str(p.relative_to(SRC)): p.read_text(encoding="utf-8") for p in SRC.rglob("*.py")}


def test_only_execute_tool_runs_a_tool_handler() -> None:
    """A registered tool's handler is called in one place, where its run is recorded."""
    callers = {f for f, text in _sources().items() if re.search(r"\bspec\.handler\(", text)}
    assert callers == {"interfaces/ai/tools/base.py"}


def test_claude_is_called_only_where_usage_is_recorded() -> None:
    """Every Messages API call answers through the agent loop's `absorb` or a recorded stream.

    The one exception is the one-token API-key check, which answers nobody.
    """
    pattern = re.compile(r"messages(?:_api\([^)]*\))?\.(?:create|stream)\(|_call_client_create\(")
    calls = {
        f: [line.strip() for line in text.splitlines() if pattern.search(line)]
        for f, text in _sources().items()
    }
    calls = {f: lines for f, lines in calls.items() if lines}
    assert set(calls) == {"interfaces/ai/agent.py", "interfaces/ai/client.py"}
    agent_calls = [c for c in calls["interfaces/ai/agent.py"] if not c.startswith("async def")]
    assert agent_calls and all("loop.absorb(" in c for c in agent_calls)
    client_text = _sources()["interfaces/ai/client.py"]
    assert len(calls["interfaces/ai/client.py"]) == 2
    assert "on_usage(await stream.get_final_message())" in client_text
    assert "max_tokens=1," in client_text


# --- the charts telemetry feeds ----------------------------------------------------------------


def test_usage_history_charts_tokens_per_day_by_kind(client: TestClient) -> None:
    """Tokens per day are stacked by kind and only the kinds that occurred are drawn."""
    with db_session() as conn:
        record_usage(conn, ADMIN_USER, "m", {"input": 100, "output": 20})
        record_usage(conn, ADMIN_USER, "m", {"input": 1, "cache_read": 900})
    res = _run("usage_history", {"days": 2})
    tile = next(t for t in res.tiles if t.id == "usage-tokens-daily")
    names = [s["name"] for s in tile.props["series"]]
    assert names == ["Input", "Output", "Cache read"] and tile.props["stacked"]
    assert res.data["tokens_per_day"]["per_day"] == {
        "Input": [0, 101],
        "Output": [0, 20],
        "Cache read": [0, 900],
    }


def test_action_history_charts_runs_per_day_and_the_most_used(client: TestClient) -> None:
    """Runs per day by outcome, and the most used actions; the history call itself counts."""
    assert "No actions run" in _run("action_history").summary
    _run("list_instances")
    _run("list_instances")
    _run("show", {"tiles": []})
    res = _run("action_history", {"days": 3})
    assert "4 action run(s) in the last 3 days, 1 failed." == res.summary
    assert res.data["per_day"] == {"Succeeded": [0, 0, 3], "Failed": [0, 0, 1]}
    top = res.tiles[1].props
    assert top["labels"] == ["list_instances", "action_history", "show"]
    assert top["series"][0]["values"] == [2.0, 1.0, 1.0]
    assert res.data["actions"][0] == {
        "name": "list_instances",
        "runs": 2,
        "failed": 0,
        "avg_ms": res.data["actions"][0]["avg_ms"],
    }


def test_team_usage_is_for_administrators_and_covers_everyone(client: TestClient) -> None:
    """An administrator sees every person; a consultant is refused, and sees only their own."""
    with db_session() as conn:
        record_usage(conn, ADMIN_USER, "m", {"input": 10})
        with owner_scope(ANA):
            record_usage(conn, ANA_USER, "m", {"output": 5})
    with owner_scope(ANA):
        _run("list_instances", user=ANA_USER)
        refused = _run("team_usage", user=ANA_USER)
        own = _run("usage_history", {"days": 1}, user=ANA_USER)
    assert not refused.ok and "Only administrators" in refused.summary
    assert own.data["tokens_per_day"]["per_day"] == {"Output": [5]}
    res = _run("team_usage", {"days": 1})
    assert res.data["tokens_by_person"] == {LOCAL_EMAIL: 10, ANA: 5}
    # Ana's three runs: the list, the refused team view, and her own history.
    assert res.data["actions_by_person"] == {ANA: 3}
    assert "15 tokens and 3 action run(s) across 2 person(s)" in res.summary
    assert [t.id for t in res.tiles] == ["team-tokens-daily", "team-tokens", "team-actions"]


def test_team_usage_without_activity_shows_nothing(client: TestClient) -> None:
    """No usage and no runs: no charts, and the summary says so with zeros."""
    res = _run("team_usage", {"days": 1})
    assert res.tiles == [] and "0 tokens and 0 action run(s) across 0 person(s)" in res.summary


def test_telemetry_repository_scopes_reads_to_the_owner(client: TestClient) -> None:
    """Without `everyone`, a person's aggregates never include someone else's."""
    with db_session() as conn:
        with owner_scope(ANA):
            record_usage(conn, ANA_USER, "m", {"input": 3})
        repo = TelemetryRepository(conn)
        assert repo.daily_tokens("2000-01-01") == {}
        assert list(repo.daily_tokens("2000-01-01", everyone=True).values())[0]["input_tokens"] == 3
