"""Tests for the Otto tool registry and Claude tool-calling agent (in-memory fakes only)."""

from dataclasses import dataclass, field
from typing import Any

import typer
from fastapi.testclient import TestClient

from now_workbench.ai.agent import run_agent
from now_workbench.ai.tools import REGISTRY, ToolContext, execute_tool
from now_workbench.api.app import create_app
from now_workbench.cli import app as cli_app
from now_workbench.db import InstanceCreate, db_session

CLI_EXCLUDED = {"serve", "version"}


def _cli_leaves(cmd: Any, prefix: str = "") -> list[str]:
    if hasattr(cmd, "commands"):
        out: list[str] = []
        for name, sub in cmd.commands.items():
            out += _cli_leaves(sub, f"{prefix} {name}".strip())
        return out
    return [prefix]


def test_every_cli_command_has_an_agent_tool() -> None:
    """Parity gate: any new CLI command must also be exposed as an Otto tool."""
    covered: set[str] = set()
    for spec in REGISTRY.values():
        covered.update(p.strip() for p in spec.cli_equivalent.split(","))
    leaves = set(_cli_leaves(typer.main.get_command(cli_app))) - CLI_EXCLUDED
    assert leaves - covered == set()


# -- In-memory fake Claude client ------------------------------------------------
@dataclass
class _Block:
    type: str
    text: str = ""
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class _Resp:
    content: list[_Block]
    stop_reason: str


class _FakeMessages:
    def __init__(self, script: list[_Resp]) -> None:
        self.script = script
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _Resp:
        self.calls.append(kwargs)
        return self.script.pop(0)


class _FakeClient:
    def __init__(self, script: list[_Resp]) -> None:
        self.messages = _FakeMessages(script)


def _tool_call(call_id: str, name: str, args: dict[str, Any]) -> _Resp:
    return _Resp([_Block("tool_use", id=call_id, name=name, input=args)], "tool_use")


def test_agent_chains_tools_and_gates_destructive_actions() -> None:
    with db_session() as repo:
        repo.add_instance(
            InstanceCreate(id="bad", name="Bad One", url="fake://auth-failed.service-now.com")
        )
        client = _FakeClient(
            [
                _tool_call("t1", "test_instances", {}),
                _tool_call("t2", "delete_instances", {"filter": "unauthenticated"}),
                _Resp([_Block("text", text="Waiting for your confirmation.")], "end_turn"),
            ]
        )
        resp = run_agent("delete failing instances", [], repo, client, "claude-test")
        assert resp.summary == "Waiting for your confirmation."
        confirm = [t for t in resp.tiles if t.id == "tile-confirm-delete_instances"]
        assert confirm, "destructive tool must produce a confirmation tile"
        assert "Bad One" in confirm[0].props["body"]
        assert repo.get_instance("bad") is not None  # not deleted yet
        # tool results were sent back to the model
        last_user = client.messages.calls[-1]["messages"][-1]
        assert last_user["content"][0]["type"] == "tool_result"

        ctx = ToolContext(repo=repo)
        done = execute_tool(ctx, "delete_instances", {"filter": "unauthenticated"}, confirmed=True)
        assert done.ok and repo.get_instance("bad") is None


def test_agent_plain_answer_without_tools() -> None:
    with db_session() as repo:
        client = _FakeClient([_Resp([_Block("text", text="Hello there.")], "end_turn")])
        resp = run_agent("hi", [], repo, client, "claude-test")
        assert resp.summary == "Hello there."
        assert resp.tiles[0].type == "rich-text"


def test_tools_cover_instance_bundle_seed_and_settings_actions() -> None:
    with db_session() as repo:
        ctx = ToolContext(repo=repo, fake_mode=True)

        renamed = execute_tool(
            ctx, "rename_instance", {"instance": "default-instance", "new_name": "Main Dev"}
        )
        inst = repo.get_instance("default-instance")
        assert renamed.ok and inst is not None and inst.name == "Main Dev"

        repo.add_instance(
            InstanceCreate(id="b", name="Second", url="fake://second.service-now.com")
        )
        assert execute_tool(ctx, "set_default_instance", {"instance": "Second"}).ok
        default = repo.get_default_instance()
        assert default is not None and default.id == "b"
        assert not execute_tool(ctx, "rename_instance", {"instance": "zzz", "new_name": "x"}).ok

        assert execute_tool(ctx, "list_bundles", {}).tiles[0].type == "data-table"
        assert execute_tool(ctx, "inspect_bundle", {"bundle_id": "sample-ai-assistant"}).ok
        assert execute_tool(ctx, "get_properties", {"bundle_id": "sample-ai-assistant"}).ok

        seeded = execute_tool(ctx, "seed_bundle", {"bundle_id": "sample-ai-assistant"})
        assert seeded.ok, seeded.summary
        op_id = seeded.data["operation_id"]
        hist = execute_tool(ctx, "seed_history", {})
        assert op_id in str(hist.tiles[0].props["rows"])

        pending = execute_tool(ctx, "rollback_seed", {"operation_id": op_id})
        assert pending.pending
        rolled = execute_tool(ctx, "rollback_seed", {"operation_id": op_id}, confirmed=True)
        assert rolled.ok

        assert execute_tool(ctx, "update_settings", {"theme_mode": "dark"}).ok
        assert repo.get_workbench_preferences().theme_mode == "dark"
        assert execute_tool(ctx, "reset_settings", {}).pending
        assert not execute_tool(ctx, "no_such_tool", {}).ok


def test_confirm_message_executes_tool_through_thread_api() -> None:
    with db_session() as repo:
        repo.add_instance(
            InstanceCreate(id="bad", name="Bad One", url="fake://auth-failed.service-now.com")
        )
    client = TestClient(create_app())
    thread = client.post("/api/threads", json={"title": "t"}).json()
    resp = client.post(
        f"/api/threads/{thread['id']}/messages",
        json={
            "content": "Confirmed: delete Bad One",
            "role": "user",
            "widget_type": "tool_confirm",
            "widget_data": {"tool": "delete_instances", "input": {"instances": ["bad"]}},
        },
    )
    assert resp.status_code == 200
    assert "Deleted 1 instance" in resp.json()[-1]["content"]
    with db_session() as repo:
        assert repo.get_instance("bad") is None
