# tests/test_cov_ai_core.py
# Coverage tests for the Otto AI core: tools (instances/system/base), agent, actions, tiles, client
# Author: Pierre Grothe
# Date: 2026-11-06
"""Coverage tests for the Otto AI core using in-memory fakes only (no network, no mocks)."""

import asyncio
import shutil
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import anthropic
import httpx
import pytest

from now_workbench.ai import agent as agent_mod
from now_workbench.ai import client as client_mod
from now_workbench.ai.actions import execute_autonomous_action
from now_workbench.ai.agent import (
    AgentEventType,
    AgentUnavailableError,
    ClaudeAgentRunner,
    ConversationFiles,
    _assemble,
    _block_to_dict,
    _call_client_create,
    _history_to_messages,
    _result_content,
    run_agent,
)
from now_workbench.ai.client import OttoClient, validate_api_key
from now_workbench.ai.tiles import (
    GenerativeUIResponse,
    UITileSpec,
    build_instance_response,
    format_instance_status,
    resolve_query_to_tiles,
)
from now_workbench.ai.tools import REGISTRY, ToolContext, execute_tool, tool_definitions
from now_workbench.ai.tools.base import ToolResult, ToolSpec, resolve_instance, run_async
from now_workbench.db import ChatMessageRecord, InstanceCreate, db_session


def _ctx(repo: Any) -> ToolContext:
    return ToolContext(repo=repo, fake_mode=True)


def _add(repo: Any, ident: str, name: str, url: str, default: bool = False) -> None:
    repo.add_instance(InstanceCreate(id=ident, name=name, url=url, is_default=default))


# -- tools/base.py ---------------------------------------------------------------
def test_resolve_instance_without_default_raises() -> None:
    with db_session() as repo:
        for i in repo.list_instances():
            repo.delete_instance(i.id)
        with pytest.raises(ValueError, match="No default instance"):
            resolve_instance(repo, None)


def test_resolve_instance_ambiguous_and_missing() -> None:
    with db_session() as repo:
        _add(repo, "a1", "Alpha One", "fake://alpha-one.service-now.com")
        _add(repo, "a2", "Alpha Two", "fake://alpha-two.service-now.com")
        with pytest.raises(ValueError, match="ambiguous"):
            resolve_instance(repo, "alpha")
        with pytest.raises(ValueError, match="No instance matches"):
            resolve_instance(repo, "zzz-nothing")
        assert resolve_instance(repo, "Alpha-One").id == "a1"
        assert resolve_instance(repo, "one.service").id == "a1"


async def test_run_async_inside_running_loop_uses_thread() -> None:
    async def value() -> int:
        return 7

    assert run_async(value()) == 7


def test_run_async_without_loop() -> None:
    async def value() -> int:
        return 5

    assert run_async(value()) == 5


def test_execute_tool_unknown_name() -> None:
    with db_session() as repo:
        res = execute_tool(_ctx(repo), "no_such_tool", {})
        assert not res.ok and "Unknown tool" in res.summary


def test_execute_tool_plan_failure_reports_error() -> None:
    def bad_plan(ctx: ToolContext, args: dict[str, Any]) -> str:
        raise RuntimeError("plan boom")

    def handler(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
        raise RuntimeError("handler boom")

    REGISTRY["zz_cov_tool"] = ToolSpec(
        name="zz_cov_tool",
        description="x",
        properties={},
        handler=handler,
        destructive=True,
        plan=bad_plan,
    )
    try:
        with db_session() as repo:
            res = execute_tool(_ctx(repo), "zz_cov_tool", {})
            assert not res.ok and "Could not prepare" in res.summary
            res2 = execute_tool(_ctx(repo), "zz_cov_tool", {}, confirmed=True)
            assert not res2.ok and "handler boom" in res2.summary
    finally:
        del REGISTRY["zz_cov_tool"]


def test_execute_tool_destructive_without_planner_uses_default_plan() -> None:
    def handler(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
        return ToolResult(summary="done")

    REGISTRY["zz_cov_noplan"] = ToolSpec(
        name="zz_cov_noplan", description="x", properties={}, handler=handler, destructive=True
    )
    try:
        with db_session() as repo:
            res = execute_tool(_ctx(repo), "zz_cov_noplan", {})
            assert res.pending and "Run zz_cov_noplan." in res.summary
    finally:
        del REGISTRY["zz_cov_noplan"]


def test_tool_definitions_lists_every_registered_tool() -> None:
    names = {d["name"] for d in tool_definitions()}
    assert names == set(REGISTRY)


# -- tools/instances.py ----------------------------------------------------------
def test_instance_tools_add_update_test_and_list() -> None:
    with db_session() as repo:
        ctx = _ctx(repo)
        added = execute_tool(
            ctx, "add_instance", {"url": "fake://newbie.service-now.com/", "make_default": True}
        )
        assert added.ok and "newbie" in added.summary
        assert any(i.name == "newbie" and i.is_default for i in repo.list_instances())

        listed = execute_tool(ctx, "list_instances", {"detailed": True})
        assert listed.ok and listed.tiles[0].type == "instance-card"

        none = execute_tool(ctx, "update_instance", {"instance": "newbie"})
        assert not none.ok and "No fields" in none.summary

        upd = execute_tool(ctx, "update_instance", {"instance": "newbie", "purpose": "test"})
        assert upd.ok and "purpose" in upd.summary
        pw = execute_tool(ctx, "update_instance", {"instance": "newbie", "password": "pw"})
        assert pw.ok and "credentials" in pw.summary

        tested = execute_tool(ctx, "test_instances", {"instances": ["newbie"]})
        assert tested.ok and tested.data["results"][0].startswith("newbie:")
        all_tested = execute_tool(ctx, "test_instances", {})
        assert len(all_tested.data["results"]) == len(repo.list_instances())


def test_instance_tools_delete_modes_and_default_fallback() -> None:
    with db_session() as repo:
        ctx = _ctx(repo)
        _add(repo, "x1", "Ex One", "fake://ex-one.service-now.com")
        _add(repo, "x2", "Ex Two", "fake://ex-two.service-now.com")
        nothing = execute_tool(ctx, "delete_instances", {"instances": []}, confirmed=True)
        assert "nothing deleted" in nothing.summary
        plan = execute_tool(ctx, "delete_instances", {"instances": []})
        assert "No matching instances" in plan.summary

        plan2 = execute_tool(ctx, "delete_instances", {"filter": "all_except_default"})
        assert plan2.pending and "Ex One" in plan2.summary
        done = execute_tool(ctx, "delete_instances", {"filter": "all_except_default"}, True)
        assert "Deleted 2" in done.summary
        assert [i.id for i in repo.list_instances()] == ["default-instance"]

        # deleting the default promotes the remaining instance
        _add(repo, "x3", "Ex Three", "fake://ex-three.service-now.com")
        execute_tool(ctx, "delete_instances", {"instances": ["default-instance"]}, True)
        remaining = repo.list_instances()
        assert [i.id for i in remaining] == ["x3"] and remaining[0].is_default


def test_instance_tools_delete_many_truncates_names() -> None:
    with db_session() as repo:
        ctx = _ctx(repo)
        for n in range(9):
            _add(repo, f"m{n}", f"Many{n}", f"fake://many{n}.service-now.com")
        plan = execute_tool(ctx, "delete_instances", {"filter": "all_except_default"})
        assert plan.summary.rstrip().endswith("...")
        done = execute_tool(ctx, "delete_instances", {"filter": "all_except_default"}, True)
        assert "..." in done.summary


def test_instance_tool_test_many_unauthenticated_in_summary() -> None:
    with db_session() as repo:
        for n in range(5):
            _add(repo, f"u{n}", f"Un{n}", f"fake://auth-failed.u{n}.service-now.com")
        res = execute_tool(_ctx(repo), "test_instances", {})
        assert res.ok and res.tiles[0].type == "instance-kpi"


def test_instance_tools_delete_unauthenticated_filter() -> None:
    with db_session() as repo:
        _add(repo, "bad", "Bad", "fake://auth-failed.service-now.com")
        execute_tool(_ctx(repo), "test_instances", {})
        res = execute_tool(
            _ctx(repo), "delete_instances", {"filter": "unauthenticated"}, confirmed=True
        )
        assert repo.get_instance("bad") is None and res.ok


# -- tools/system.py -------------------------------------------------------------
def test_system_tools_settings_roundtrip_and_diagnostics() -> None:
    with db_session() as repo:
        ctx = _ctx(repo)
        shown = execute_tool(ctx, "show_settings", {})
        assert shown.ok and "anthropic_api_key_masked" not in shown.data["settings"]

        empty = execute_tool(ctx, "update_settings", {"bogus": 1})
        assert not empty.ok

        key = next(iter(REGISTRY["update_settings"].properties))
        spec = REGISTRY["update_settings"].properties[key]
        value: Any = {"boolean": True, "integer": 3}.get(spec["type"], "val")
        changed = execute_tool(ctx, "update_settings", {key: value})
        assert changed.ok and changed.data["changed"] == {key: value}

        plan = execute_tool(ctx, "reset_settings", {})
        assert plan.pending and "factory defaults" in plan.summary
        reset = execute_tool(ctx, "reset_settings", {}, confirmed=True)
        assert reset.ok and "reset" in reset.summary

        diag = execute_tool(ctx, "run_diagnostics", {})
        assert diag.ok and diag.tiles[0].id == "tile-doctor"
        assert "instances" in diag.tiles[0].props["rows"][-2]


def test_model_to_text_truncates_long_payloads() -> None:
    from now_workbench.ai.tools.base import model_to_text

    out = model_to_text({"k": "x" * 50}, limit=10)
    assert out.endswith("...[truncated]") and len(out) == 10 + len("...[truncated]")


# -- agent.py --------------------------------------------------------------------
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


class _AsyncMessages:
    def __init__(self, script: list[_Resp]) -> None:
        self.script = script

    async def create(self, **kwargs: Any) -> _Resp:
        return self.script.pop(0)


class _AsyncClient:
    def __init__(self, script: list[_Resp]) -> None:
        self.messages = _AsyncMessages(script)


class _AwaitableMessages:
    """Sync callable that returns an awaitable (neither a coroutine function nor plain)."""

    def __init__(self, resp: _Resp) -> None:
        self.resp = resp

    def create(self, **kwargs: Any) -> asyncio.Future[_Resp]:
        fut: asyncio.Future[_Resp] = asyncio.get_running_loop().create_future()
        fut.set_result(self.resp)
        return fut


class _NoCreate:
    messages = object()


class _Boom:
    class messages:  # noqa: N801 - mimics the SDK attribute shape
        @staticmethod
        def create(**kwargs: Any) -> _Resp:
            raise RuntimeError("api down")


def _tool_call(call_id: str, name: str, args: dict[str, Any]) -> _Resp:
    return _Resp([_Block("tool_use", id=call_id, name=name, input=args)], "tool_use")


def _text(msg: str) -> _Resp:
    return _Resp([_Block("text", text=msg)], "end_turn")


def _msg(mid: str, role: str, content: str) -> ChatMessageRecord:
    return ChatMessageRecord(id=mid, thread_id="t", role=role, content=content)


def test_make_client_builds_anthropic_clients() -> None:
    assert isinstance(agent_mod.make_client("k"), anthropic.Anthropic)
    assert isinstance(agent_mod.make_async_client("k"), anthropic.AsyncAnthropic)


def test_history_to_messages_merges_roles_files_and_drops_leading_assistant() -> None:
    img = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "x"}}
    history = [
        _msg("a0", "assistant", "stale greeting"),
        _msg("u1", "user", "first"),
        _msg("u2", "user", "second"),
        _msg("a1", "assistant", ""),
        _msg("u3", "user", ""),
        _msg("a2", "assistant", "reply"),
        _msg("s1", "system", "ignored"),
    ]
    out = _history_to_messages(history, "latest", files={"u3": [img]}, current_files=[img])
    assert out[0]["role"] == "user"
    # u1+u2 merged as strings; u3 (file only) joins the block list
    assert out[0]["content"][0]["text"] == "first\nsecond"
    assert out[0]["content"][1] == img
    assert out[0]["content"][2]["text"] == "(see the attached files)"
    assert out[1] == {"role": "assistant", "content": "reply"}
    assert out[2]["role"] == "user" and out[2]["content"][-1]["text"] == "latest"


def test_history_to_messages_joins_string_after_blocks() -> None:
    img = {"type": "image", "source": {}}
    out = _history_to_messages([_msg("u1", "user", "a")], "b", current_files=[img])
    assert out[0]["content"][0] == {"type": "text", "text": "a"}
    assert out[0]["content"][1] == img


def test_block_to_dict_covers_every_block_kind() -> None:
    @dataclass
    class B:
        type: str
        thinking: str = "t"
        signature: str = "s"
        data: str = "d"

    assert _block_to_dict(B("thinking")) == {"type": "thinking", "thinking": "t", "signature": "s"}
    assert _block_to_dict(B("redacted_thinking")) == {"type": "redacted_thinking", "data": "d"}
    assert _block_to_dict(B("server_tool_use")) is None


def test_result_content_attaches_png_and_jpeg_images() -> None:
    res = ToolResult(summary="shot", images=["/9j/abc", "iVBOR"])
    content = _result_content(res)
    assert isinstance(content, list)
    assert content[1]["source"]["media_type"] == "image/jpeg"
    assert content[2]["source"]["media_type"] == "image/png"


def test_assemble_layouts_and_fallback_summary() -> None:
    def tile(i: str, kind: str = "rich-text") -> UITileSpec:
        return UITileSpec(id=i, type=kind)  # type: ignore[arg-type]

    assert _assemble("", []).summary == "Done."
    two = _assemble("x", [ToolResult(summary="a", tiles=[tile("1"), tile("2")])])
    assert two.layout == "2-col"
    three = _assemble("x", [ToolResult(summary="a", tiles=[tile("1"), tile("2"), tile("3")])])
    assert three.layout == "3-col"
    table = _assemble("x", [ToolResult(summary="a", tiles=[tile("1"), tile("2", "data-table")])])
    assert table.layout == "1-col"
    replaced = _assemble(
        "", [ToolResult(summary="a", tiles=[tile("1")]), ToolResult(summary="b", tiles=[tile("1")])]
    )
    assert len(replaced.tiles) == 1 and replaced.summary == "b"


async def test_call_client_create_supports_all_client_shapes() -> None:
    assert (await _call_client_create(_AsyncClient([_text("a")]), model="m")).stop_reason == (
        "end_turn"
    )
    assert (await _call_client_create(_FakeClient([_text("b")]), model="m")).content[0].text == "b"
    awaitable = _FakeClient([])
    awaitable.messages = _AwaitableMessages(_text("c"))  # type: ignore[assignment]
    assert (await _call_client_create(awaitable, model="m")).content[0].text == "c"
    with pytest.raises(AgentUnavailableError):
        await _call_client_create(_NoCreate())


async def test_runner_streams_events_and_assembles_response() -> None:
    with db_session() as repo:
        client = _AsyncClient(
            [
                _Resp(
                    [
                        _Block("text", text="Checking."),
                        _Block("tool_use", "u1", name="list_instances"),
                    ],
                    "tool_use",
                ),
                _text("All good."),
            ]
        )
        runner = ClaudeAgentRunner(client, "m", repo, fake_mode=True)
        events = [e async for e in runner.stream_run("how many", [])]
        kinds = [e.event_type for e in events]
        assert kinds == [
            AgentEventType.TEXT_DELTA,
            AgentEventType.TOOL_CALL_START,
            AgentEventType.TOOL_CALL_RESULT,
            AgentEventType.TILE_RENDER,
            AgentEventType.TEXT_DELTA,
            AgentEventType.DONE,
        ]
        client2 = _AsyncClient([_tool_call("u1", "list_instances", {}), _text("Done now.")])
        resp = await ClaudeAgentRunner(client2, "m", repo, fake_mode=True).run(
            "q", [], ConversationFiles(by_message={}, current=[])
        )
        assert resp.summary == "Done now." and resp.steps[0].ok


async def test_runner_tool_without_tiles_emits_no_tile_event() -> None:
    with db_session() as repo:
        client = _AsyncClient([_tool_call("u1", "no_such_tool", {}), _text("ok")])
        events = [e async for e in ClaudeAgentRunner(client, "m", repo).stream_run("q", [])]
        assert AgentEventType.TILE_RENDER not in [e.event_type for e in events]


async def test_runner_failure_fake_mode_raises_and_live_mode_yields_diagnostic() -> None:
    with db_session() as repo:
        with pytest.raises(AgentUnavailableError, match="api down"):
            await ClaudeAgentRunner(_Boom(), "m", repo, fake_mode=True).run("q", [])
        resp = await ClaudeAgentRunner(_Boom(), "m", repo).run("q", [])
        assert resp.summary == "Diagnostic Warning: api down"
        assert resp.tiles[0].type == "security-alert"


async def test_runner_run_without_done_event_returns_placeholder() -> None:
    class Silent(ClaudeAgentRunner):
        async def stream_run(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
            if False:
                yield None

    with db_session() as repo:
        resp = await Silent(_Boom(), "m", repo).run("q", [])
        assert resp.summary == "No response received from agent."


def test_run_agent_sync_context_and_failure_paths() -> None:
    with db_session() as repo:
        files = ConversationFiles(by_message={}, current=[])
        resp = run_agent("hi", [], repo, _FakeClient([_text("hello")]), "m", files=files)
        assert resp.summary == "hello"


async def test_run_agent_inside_running_loop_uses_sync_runner() -> None:
    with db_session() as repo:
        client = _FakeClient([_tool_call("t1", "list_instances", {}), _text("listed")])
        resp = run_agent("list", [], repo, client, "m", fake_mode=True)
        assert resp.summary == "listed" and resp.steps
        # tool_result was fed back with a single cache breakpoint
        call = client.messages.calls[-1]
        assert call["cache_control"] == {"type": "ephemeral"}
        assert call["system"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
        with pytest.raises(AgentUnavailableError):
            run_agent("x", [], repo, _Boom(), "m", fake_mode=True)
        diag = run_agent("x", [], repo, _Boom(), "m")
        assert diag.tiles[0].id == "tile-diagnostic-error"


def test_run_agent_sync_without_tools_skips_cache_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_mod, "tool_definitions", lambda: [])
    with db_session() as repo:
        client = _FakeClient([_text("none")])
        agent_mod._run_agent_sync("q", [], repo, client, "m")
        assert client.messages.calls[0]["tools"] == []


async def test_runner_without_tools_skips_cache_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_mod, "tool_definitions", lambda: [])
    with db_session() as repo:
        resp = await ClaudeAgentRunner(_AsyncClient([_text("none")]), "m", repo).run("q", [])
        assert resp.summary == "none"


def test_resolve_instance_blank_returns_default_and_media_tile_shape() -> None:
    from now_workbench.ai.tools.base import media_tile

    with db_session() as repo:
        assert resolve_instance(repo, None).id == "default-instance"
    tile = media_tile("m1", "Clip", "http://x/y.mp4", label="L")
    assert tile.type == "media-player"
    assert tile.props == {
        "url": "http://x/y.mp4",
        "media_type": "video",
        "label": "L",
        "actions": [],
    }


def test_instance_tools_rename_and_set_default() -> None:
    with db_session() as repo:
        ctx = _ctx(repo)
        _add(repo, "r1", "Rename Me", "fake://rename.service-now.com")
        renamed = execute_tool(ctx, "rename_instance", {"instance": "r1", "new_name": " New "})
        assert renamed.ok and repo.get_instance("r1").name == "New"  # type: ignore[union-attr]
        made = execute_tool(ctx, "set_default_instance", {"instance": "r1"})
        assert made.ok and repo.get_default_instance().id == "r1"  # type: ignore[union-attr]


# -- actions.py ------------------------------------------------------------------
def test_actions_verify_instances_reports_counts() -> None:
    with db_session() as repo:
        _add(repo, "bad", "Bad Box", "fake://auth-failed.service-now.com")
        res = execute_autonomous_action("please test all instances in detail", repo)
        assert res is not None
        assert "Checked live authentication across 2 instance(s)" in res.summary
        assert res.tiles[0].type == "instance-card"
        brief = execute_autonomous_action("verify instance now", repo)
        assert brief is not None and brief.tiles[0].type == "instance-kpi"


def test_actions_delete_instances_previews_only() -> None:
    with db_session() as repo:
        _add(repo, "bad", "Bad Box", "fake://auth-failed.service-now.com")
        named = execute_autonomous_action("delete the bad box instance", repo)
        assert named is not None and "Nothing was deleted" in named.summary
        assert "Bad Box" in named.summary
        none = execute_autonomous_action("remove the zzz instances", repo)
        assert none is not None and "No matching" in none.summary
        assert repo.get_instance("bad") is not None
        secondary = execute_autonomous_action("purge secondary instances", repo)
        assert secondary is not None and "Bad Box" in secondary.summary
        unauth = execute_autonomous_action("delete unreachable stuff", repo)
        assert unauth is not None
        assert execute_autonomous_action("delete the widgets", repo) is None


def test_actions_switch_default_and_add_instance() -> None:
    with db_session() as repo:
        _add(repo, "sw", "Switchy", "fake://switchy.service-now.com")
        sw = execute_autonomous_action("make default switchy", repo)
        assert sw is not None and "Switched primary default target to 'Switchy'" in sw.summary
        assert repo.get_default_instance().id == "sw"  # type: ignore[union-attr]
        assert execute_autonomous_action("set default nothing-here", repo) is None

        before = len(repo.list_instances())
        add = execute_autonomous_action("add instance https://foo.service-now.com/", repo)
        assert add is not None and "Nothing was registered" in add.summary
        assert len(repo.list_instances()) == before
        assert execute_autonomous_action("add instance please", repo) is None


def test_actions_delete_bundle_preview_and_misses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sample = Path(__file__).resolve().parent.parent / "bundles" / "hr-onboarding-ai"
    shutil.copytree(sample, tmp_path / "hr-onboarding-ai")
    monkeypatch.setenv("WORKBENCH_BUNDLES_DIR", str(tmp_path))
    with db_session() as repo:
        res = execute_autonomous_action("delete the hr-onboarding-ai bundle", repo)
        assert res is not None and "Nothing was deleted" in res.summary
        assert (tmp_path / "hr-onboarding-ai").is_dir()
        assert execute_autonomous_action("delete the demo nonexistent-xyz", repo) is None
        assert execute_autonomous_action("tell me a joke", repo) is None


# -- tiles.py --------------------------------------------------------------------
def test_format_instance_status_known_fallback_and_default() -> None:
    assert format_instance_status("AUTH_FAILED") == "Auth Failed (HTTP 401/403)"
    assert format_instance_status("weird", "Custom") == "Custom"
    assert format_instance_status("weird") == "Unverified (Not Tested)"
    assert format_instance_status(None) == "Unverified (Not Tested)"


def test_build_instance_response_empty_and_accent_colors() -> None:
    empty = build_instance_response([])
    assert "no ServiceNow instances" in empty.summary
    assert empty.tiles[0].props["accent"] == "amber"
    red = build_instance_response([{"id": "a", "name": "A", "status": "error"}])
    assert red.tiles[0].props["accent"] == "red"
    green = build_instance_response([{"id": "a", "name": "A", "status": "authenticated"}])
    assert green.tiles[0].props["accent"] == "green"
    assert "Delete Unauthenticated" not in str(green.tiles[0].props["actions"])


def test_build_instance_response_detailed_layouts() -> None:
    def insts(n: int) -> list[dict[str, Any]]:
        return [{"id": f"i{k}", "name": f"I{k}", "is_default": k == 0} for k in range(n)]

    one = build_instance_response(insts(1), detail_level="detailed")
    two = build_instance_response(insts(2), detail_level="detailed")
    three = build_instance_response(insts(3), detail_level="detailed")
    assert (one.layout, two.layout, three.layout) == ("1-col", "2-col", "3-col")
    first_ids = [a["id"] for a in two.tiles[0].props["actions"]]
    second_ids = [a["id"] for a in two.tiles[1].props["actions"]]
    assert "activate" not in first_ids and "activate" in second_ids


def test_resolve_query_to_tiles_routes_every_inquiry_kind() -> None:
    inst = resolve_query_to_tiles("how many instances do I have")
    assert inst.tiles[0].type == "instance-kpi"
    assert resolve_query_to_tiles("list my instances", instances=[]).summary.startswith("You have")
    assert resolve_query_to_tiles("targets").tiles
    detailed = resolve_query_to_tiles("show details of instances")
    assert detailed.tiles[0].type == "instance-card"
    assert resolve_query_to_tiles("any security risks").tiles[0].type == "security-alert"
    assert resolve_query_to_tiles("fluent schema").tiles[0].type == "fluent-schema"
    recipes = resolve_query_to_tiles("why recipes over update sets")
    assert [t.id for t in recipes.tiles] == ["tile-recipe-why", "tile-recipe-compat"]
    assert resolve_query_to_tiles("sys_update_xml").layout == "2-col"
    fallback = resolve_query_to_tiles("tell me a story")
    assert fallback.tiles[0].id == "tile-rich-guidance"


def test_resolve_query_to_tiles_bundle_summary_and_detail() -> None:
    counted = resolve_query_to_tiles("how many demo bundles")
    assert counted.tiles[0].id == "tile-bundle-kpi"
    assert "2 declarative demo recipe bundles" in counted.summary
    listed = resolve_query_to_tiles("list the demo bundles")
    assert listed.layout == "2-col" and listed.tiles[0].type == "demo-bundle"
    one = resolve_query_to_tiles(
        "show bundles", bundles=[{"id": "b1", "name": "Solo", "tables_count": 1}]
    )
    assert one.layout == "1-col" and one.summary.startswith("You have 1 demo bundle ")
    single_kpi = resolve_query_to_tiles(
        "count bundles", bundles=[{"tables_count": 2, "records_count": 5}]
    )
    assert "2 Fluent Tables / 5 Seed Records" in single_kpi.tiles[0].props["subtitle"]
    fallback_ids = resolve_query_to_tiles("show bundles", bundles=[{}])
    assert fallback_ids.tiles[0].id == "tile-bundle-0"


# -- client.py -------------------------------------------------------------------
class _Stream:
    def __init__(self, chunks: list[str], fail: bool = False) -> None:
        self.chunks = chunks
        self.fail = fail

    async def __aenter__(self) -> _Stream:
        if self.fail:
            raise RuntimeError("stream broke")
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    @property
    def text_stream(self) -> Iterator[str]:  # consumed with async for below
        return self._gen()  # type: ignore[return-value]

    async def _gen(self) -> Any:
        for c in self.chunks:
            yield c


class _StreamMessages:
    def __init__(self, stream: _Stream) -> None:
        self.stream_obj = stream
        self.kwargs: dict[str, Any] = {}

    def stream(self, **kwargs: Any) -> _Stream:
        self.kwargs = kwargs
        return self.stream_obj


class _StreamClient:
    def __init__(self, stream: _Stream) -> None:
        self.messages = _StreamMessages(stream)


async def _collect(otto: OttoClient, messages: list[dict[str, Any]], **kw: Any) -> str:
    return "".join([c async for c in otto.stream_chat(messages, **kw)])


def test_otto_client_builds_async_client_only_with_key() -> None:
    assert OttoClient().client is None
    assert isinstance(OttoClient(api_key="sk-ant-x").client, anthropic.AsyncAnthropic)


def test_otto_simulate_response_branches() -> None:
    otto = OttoClient()
    assert "build or error" in otto._simulate_response("Build failed")[0]
    assert "Table(" in otto._simulate_response("fluent schema")[0]
    assert "DemoHub vs Now Workbench" in otto._simulate_response("demohub")[0]
    assert "Instance & Configuration" in otto._simulate_response("my api key")[0]
    assert "I received" in otto._simulate_response("zzz")[0]


async def test_otto_stream_chat_simulation_mode_with_and_without_messages() -> None:
    otto = OttoClient()
    out = await _collect(otto, [{"role": "user", "content": "error please"}], context={"a": 1})
    assert "simulation mode" in out and "build or error" in out
    assert "I received" in await _collect(otto, [])


async def test_otto_stream_chat_streams_with_cache_markers_and_reports_errors() -> None:
    stream_client = _StreamClient(_Stream(["Hel", "lo"]))
    otto = OttoClient(client=stream_client, model="m")
    msgs = [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
        {"role": "user", "content": "three"},
    ]
    assert await _collect(otto, msgs, context={"page": "x"}) == "Hello"
    sent = stream_client.messages.kwargs
    assert sent["messages"][1]["content"][0]["cache_control"] == {"type": "ephemeral"}
    assert sent["messages"][0]["content"] == "one"
    assert "[Active Workspace Context]" in sent["system"][0]["text"]

    broken = OttoClient(client=_StreamClient(_Stream([], fail=True)))
    assert "Otto error contacting Claude API: stream broke" in await _collect(broken, msgs)


class _ValidateMessages:
    def __init__(self, exc: Exception | None) -> None:
        self.exc = exc

    async def create(self, **kwargs: Any) -> None:
        if self.exc:
            raise self.exc


class _ValidateClient:
    def __init__(self, exc: Exception | None = None) -> None:
        self.messages = _ValidateMessages(exc)
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def _status_error(cls: type[anthropic.APIStatusError], code: int) -> anthropic.APIStatusError:
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("nope", response=httpx.Response(code, request=req), body=None)


async def test_validate_api_key_all_outcomes() -> None:
    assert await validate_api_key("  ") == (False, "API key cannot be empty.")
    assert (await validate_api_key("abc"))[0] is False
    assert await validate_api_key("sk-ant-test123") == (True, "Key syntax valid (test mode).")
    ok, msg = await validate_api_key("sk-ant-real", client=_ValidateClient())
    assert ok and "successfully verified" in msg
    auth = _status_error(anthropic.AuthenticationError, 401)
    ok, msg = await validate_api_key("sk-ant-real", client=_ValidateClient(auth))
    assert not ok and "authentication failed: nope" in msg
    rate = _status_error(anthropic.RateLimitError, 429)
    assert await validate_api_key("sk-ant-real", client=_ValidateClient(rate)) == (
        True,
        "Key verified (rate limit reached).",
    )
    ok, msg = await validate_api_key(
        "sk-ant-real", client=_ValidateClient(RuntimeError("Connection timeout"))
    )
    assert ok and "probe offline" in msg
    ok, msg = await validate_api_key("sk-ant-real", client=_ValidateClient(RuntimeError("weird")))
    assert not ok and msg == "Validation failed: weird"


async def test_validate_api_key_builds_default_client(monkeypatch: pytest.MonkeyPatch) -> None:
    built: list[str] = []

    made: list[_ValidateClient] = []

    def fake_async(api_key: str) -> _ValidateClient:
        built.append(api_key)
        made.append(_ValidateClient())
        return made[-1]

    monkeypatch.setattr(client_mod.anthropic, "AsyncAnthropic", fake_async)
    ok, _ = await validate_api_key(" sk-ant-live ")
    assert ok and built == ["sk-ant-live"]
    assert made[0].closed  # the client it created is closed (no leaked connection pool)


def test_generative_ui_response_defaults() -> None:
    resp = GenerativeUIResponse(summary="s")
    assert resp.layout == "auto" and resp.tiles == [] and resp.steps == []
