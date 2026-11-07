# tests/test_agent_nonblocking.py
# Otto's streaming path (/ws/otto) runs its sync tools off the event loop (STORY-075).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests that ``ClaudeAgentRunner.stream_run`` keeps the event loop free while a tool runs."""

import asyncio
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import pytest

from now_workbench.interfaces.ai.agent import AgentEventType, ClaudeAgentRunner
from now_workbench.interfaces.ai.conversation import Question
from now_workbench.interfaces.ai.tools.base import REGISTRY, ToolContext, ToolResult, ToolSpec
from now_workbench.platform.db.session import db_session
from now_workbench.platform.owner import current_owner

_TOOL_S = 0.3


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

    def create(self, **_kwargs: Any) -> _Resp:
        return self.script.pop(0)


class _FakeClient:
    def __init__(self, script: list[_Resp]) -> None:
        self.messages = _FakeMessages(script)


async def test_slow_tool_does_not_block_the_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """A concurrent task keeps ticking while a slow sync tool runs; the owner scope follows."""
    windows: list[tuple[float, float]] = []
    seen: list[tuple[str, int]] = []

    def slow_tool(_ctx: ToolContext, _args: dict[str, Any]) -> ToolResult:
        start = time.monotonic()
        time.sleep(_TOOL_S)  # a blocking instance call, as a sync tool makes it
        windows.append((start, time.monotonic()))
        seen.append((current_owner(), threading.get_ident()))
        return ToolResult(summary="slow done")

    monkeypatch.setitem(
        REGISTRY,
        "slow_probe",
        ToolSpec(name="slow_probe", description="Slow probe.", properties={}, handler=slow_tool),
    )
    client = _FakeClient(
        [
            _Resp([_Block("tool_use", id="t1", name="slow_probe")], "tool_use"),
            _Resp([_Block("tool_use", id="t2", name="slow_probe")], "tool_use"),
            _Resp([_Block("text", text="Done.")], "end_turn"),
        ]
    )

    ticks: list[float] = []
    done = asyncio.Event()

    async def ticker() -> None:
        while not done.is_set():
            ticks.append(time.monotonic())
            await asyncio.sleep(0.02)

    owner = current_owner()
    with db_session() as conn:
        runner = ClaudeAgentRunner(client=client, model="claude-test", conn=conn, fake_mode=True)
        tick_task = asyncio.create_task(ticker())
        await asyncio.sleep(0)
        events = [ev async for ev in runner.stream_run(Question("probe", []))]
        done.set()
        await tick_task

    results = [e for e in events if e.event_type == AgentEventType.TOOL_CALL_RESULT]
    assert [e.payload["summary"] for e in results] == ["slow done", "slow done"]
    final = next(e for e in events if e.event_type == AgentEventType.DONE)
    assert final.payload["response"]["summary"] == "Done."
    assert [o for o, _ in seen] == [owner, owner]
    assert all(tid != threading.get_ident() for _, tid in seen)  # never on the loop thread
    assert len(windows) == 2
    for start, end in windows:
        inside = [t for t in ticks if start < t < end]
        assert len(inside) >= 3, f"event loop blocked for {end - start:.2f}s"
