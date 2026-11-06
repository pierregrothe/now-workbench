"""Otto agent loop: Async Claude tool-calling over the shared action registry (ADR-011)."""

import inspect
from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Any

import anthropic
from pydantic import BaseModel, ConfigDict

from now_workbench.ai.tiles import AgentStep, GenerativeUIResponse, TileLayout, UITileSpec
from now_workbench.ai.tools import ToolContext, ToolResult, execute_tool, tool_definitions
from now_workbench.ai.tools.base import model_to_text, text_tile
from now_workbench.db import ChatMessageRecord, DatabaseRepository

MAX_STEPS = 6
MAX_TILES = 12

AGENT_SYSTEM_PROMPT = """You are Otto, the operator of the now-workbench ServiceNow demo tool.
You can DO things, not just describe them: use the provided tools for every request about
instances, demo bundles, seeding, properties, Fluent schemas, templates, captures, settings
and diagnostics. Every capability of the `workbench` CLI is available as a tool.

Rules:
- Act first. If the request is clear, call the tool; only ask a question when a required
  value is truly missing or a reference is ambiguous.
- Chain tools when needed (e.g. test instances, then delete the failing ones).
- When asked to test, drive, or run a demo, use 'run_demo_pipeline' (or follow testing
  with 'capture_media') so that live proof artifacts are recorded and returned as media tiles.
- Destructive tools (delete, rollback, reset, restore) are gated: the tool returns a pending
  confirmation shown to the user as a Confirm button. Say that you are waiting for
  confirmation; never claim it was done.
- The UI renders tool results as tiles. Your final reply must be 1-2 plain sentences that
  summarize what happened. No markdown, no lists, no repeating tile data.
- Never reveal or ask for the Claude API key.
"""


class AgentEventType(StrEnum):
    """Lifecycle event types emitted by ClaudeAgentRunner."""

    TEXT_DELTA = "text_delta"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_RESULT = "tool_call_result"
    TILE_RENDER = "tile_render"
    ERROR = "error"
    DONE = "done"


class AgentEvent(BaseModel):
    """Event envelope streamed to frontend or log observers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_type: AgentEventType
    payload: dict[str, Any] = {}


class AgentUnavailableError(RuntimeError):
    """Raised when the Claude agent cannot run (no key, API failure)."""


def make_client(api_key: str) -> Any:
    """Create a synchronous Anthropic client."""
    return anthropic.Anthropic(api_key=api_key)


def make_async_client(api_key: str) -> Any:
    """Create an asynchronous Anthropic client."""
    return anthropic.AsyncAnthropic(api_key=api_key)


def _history_to_messages(history: list[ChatMessageRecord], user_text: str) -> list[dict[str, Any]]:
    """Convert chat history to alternating Claude messages ending with the new user turn."""
    raw: list[tuple[str, str]] = [
        (m.role, m.content)
        for m in history
        if m.role in ("user", "assistant") and m.content.strip()
    ]
    raw.append(("user", user_text))
    merged: list[dict[str, Any]] = []
    for role, content in raw:
        if merged and merged[-1]["role"] == role:
            merged[-1]["content"] += "\n" + content
        else:
            merged.append({"role": role, "content": content})
    while merged and merged[0]["role"] != "user":
        merged.pop(0)
    return merged


def _block_to_dict(block: Any) -> dict[str, Any] | None:
    if block.type == "text":
        return {"type": "text", "text": block.text}
    if block.type == "thinking":
        return {
            "type": "thinking",
            "thinking": getattr(block, "thinking", ""),
            "signature": getattr(block, "signature", ""),
        }
    if block.type == "redacted_thinking":
        return {"type": "redacted_thinking", "data": getattr(block, "data", "")}
    if block.type == "tool_use":
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": dict(block.input)}
    return None


def _pick_layout(tiles: list[UITileSpec]) -> TileLayout:
    if len(tiles) <= 1 or any(t.type == "data-table" for t in tiles):
        return "1-col"
    return "2-col" if len(tiles) == 2 else "3-col"


def _assemble(text: str, results: list[ToolResult]) -> GenerativeUIResponse:
    """Merge tool tiles (later results replace earlier tiles with the same id)."""
    by_id: dict[str, UITileSpec] = {}
    for res in results:
        for tile in res.tiles:
            by_id.pop(tile.id, None)
            by_id[tile.id] = tile
    tiles = list(by_id.values())[-MAX_TILES:]
    summary = text.strip() or (results[-1].summary if results else "Done.")
    if not tiles:
        tiles = [text_tile("tile-otto-reply", "Otto", summary)]
    steps = [AgentStep(label=r.summary.strip().splitlines()[0][:120], ok=r.ok) for r in results]
    return GenerativeUIResponse(
        summary=summary, layout=_pick_layout(tiles), tiles=tiles, steps=steps
    )


def _build_diagnostic_error_tiles(err_msg: str) -> GenerativeUIResponse:
    """Construct an explicit diagnostic warning tile when live API fails (ADR-011)."""
    alert_tile = UITileSpec(
        id="tile-diagnostic-error",
        type="security-alert",
        title="Claude Agent Diagnostic Warning",
        props={
            "issue": f"Claude API execution encountered an error: {err_msg}",
            "severity": "HIGH",
            "remediation": (
                "Verify your Anthropic API key in Settings or review instance connectivity."
            ),
            "actions": [
                {"id": "settings", "label": "Review Settings", "variant": "primary"},
                {"id": "probe_all", "label": "Test Connectivity"},
            ],
        },
    )
    return GenerativeUIResponse(
        summary=f"Diagnostic Warning: {err_msg}",
        layout="1-col",
        tiles=[alert_tile],
    )


async def _call_client_create(client: Any, **kwargs: Any) -> Any:
    """Invoke messages.create supporting both synchronous and asynchronous clients."""
    fn = getattr(client.messages, "create", None)
    if fn is None:
        raise AgentUnavailableError("Client has no messages.create method.")
    if inspect.iscoroutinefunction(fn):
        return await fn(**kwargs)
    result = fn(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


def _execute_turn_calls(
    calls: list[Any],
    ctx: ToolContext,
) -> tuple[list[ToolResult], list[dict[str, Any]], list[AgentEvent]]:
    """Execute tool calls from an assistant turn and package results and events."""
    results: list[ToolResult] = []
    tool_results: list[dict[str, Any]] = []
    events: list[AgentEvent] = []
    for call in calls:
        events.append(
            AgentEvent(
                event_type=AgentEventType.TOOL_CALL_START,
                payload={"id": call.id, "tool": call.name, "input": dict(call.input)},
            )
        )
        res = execute_tool(ctx, call.name, dict(call.input))
        results.append(res)
        events.append(
            AgentEvent(
                event_type=AgentEventType.TOOL_CALL_RESULT,
                payload={"id": call.id, "tool": call.name, "summary": res.summary, "ok": res.ok},
            )
        )
        if res.tiles:
            events.append(
                AgentEvent(
                    event_type=AgentEventType.TILE_RENDER,
                    payload={"tiles": [t.model_dump() for t in res.tiles]},
                )
            )
        tool_results.append(
            {
                "type": "tool_result",
                "tool_use_id": call.id,
                "content": f"{res.summary}\n{model_to_text(res.data)}",
                "is_error": not res.ok,
            }
        )
    return results, tool_results, events


class ClaudeAgentRunner:
    """Async streaming agent runner with Anthropic prompt caching and real-time events."""

    def __init__(
        self,
        client: Any,
        model: str,
        repo: DatabaseRepository,
        fake_mode: bool = False,
    ) -> None:
        self.client = client
        self.model = model
        self.repo = repo
        self.fake_mode = fake_mode
        self.ctx = ToolContext(repo=repo, fake_mode=fake_mode)

    async def stream_run(
        self,
        user_text: str,
        history: list[ChatMessageRecord],
    ) -> AsyncIterator[AgentEvent]:
        """Stream granular lifecycle events through the Claude tool loop."""
        messages = _history_to_messages(history, user_text)
        tools = tool_definitions()
        if tools:
            tools[-1]["cache_control"] = {"type": "ephemeral"}

        system = [
            {
                "type": "text",
                "text": AGENT_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ]

        results: list[ToolResult] = []
        final_text = ""

        try:
            for _ in range(MAX_STEPS):
                resp = await _call_client_create(
                    self.client,
                    model=self.model,
                    max_tokens=1500,
                    system=system,
                    tools=tools,
                    messages=messages,
                )
                final_text = "".join(b.text for b in resp.content if b.type == "text")
                if final_text:
                    yield AgentEvent(
                        event_type=AgentEventType.TEXT_DELTA,
                        payload={"text": final_text},
                    )

                calls = [b for b in resp.content if b.type == "tool_use"]
                if resp.stop_reason != "tool_use" or not calls:
                    break

                blocks = [d for b in resp.content if (d := _block_to_dict(b)) is not None]
                messages.append({"role": "assistant", "content": blocks})

                step_res, step_tool_res, step_events = _execute_turn_calls(calls, self.ctx)
                results.extend(step_res)
                for ev in step_events:
                    yield ev

                if step_tool_res:
                    step_tool_res[-1]["cache_control"] = {"type": "ephemeral"}
                messages.append({"role": "user", "content": step_tool_res})

            assembled = _assemble(final_text, results)
            yield AgentEvent(
                event_type=AgentEventType.DONE,
                payload={"response": assembled.model_dump()},
            )

        except Exception as exc:
            if self.fake_mode:
                raise AgentUnavailableError(str(exc)) from exc
            err_diag = _build_diagnostic_error_tiles(str(exc))
            yield AgentEvent(event_type=AgentEventType.ERROR, payload={"error": str(exc)})
            yield AgentEvent(
                event_type=AgentEventType.DONE,
                payload={"response": err_diag.model_dump()},
            )

    async def run(
        self,
        user_text: str,
        history: list[ChatMessageRecord],
    ) -> GenerativeUIResponse:
        """Execute the agent run and return the final assembled GenerativeUIResponse."""
        final_resp: GenerativeUIResponse | None = None
        async for event in self.stream_run(user_text, history):
            if event.event_type == AgentEventType.DONE:
                raw_resp = event.payload.get("response", {})
                final_resp = GenerativeUIResponse.model_validate(raw_resp)
        if final_resp is None:
            return _assemble("No response received from agent.", [])
        return final_resp


def run_agent(
    user_text: str,
    history: list[ChatMessageRecord],
    repo: DatabaseRepository,
    client: Any,
    model: str,
    fake_mode: bool = False,
) -> GenerativeUIResponse:
    """Synchronous adapter for backward compatibility running ClaudeAgentRunner."""
    import asyncio

    runner = ClaudeAgentRunner(client=client, model=model, repo=repo, fake_mode=fake_mode)

    try:
        asyncio.get_running_loop()
        in_running_loop = True
    except RuntimeError:
        in_running_loop = False

    if in_running_loop:
        return _run_agent_sync(user_text, history, repo, client, model, fake_mode)
    return asyncio.run(runner.run(user_text, history))


def _run_agent_sync(
    user_text: str,
    history: list[ChatMessageRecord],
    repo: DatabaseRepository,
    client: Any,
    model: str,
    fake_mode: bool = False,
) -> GenerativeUIResponse:
    """Direct synchronous runner for tests and sync execution contexts."""
    ctx = ToolContext(repo=repo, fake_mode=fake_mode)
    messages = _history_to_messages(history, user_text)
    tools = tool_definitions()
    if tools:
        tools[-1]["cache_control"] = {"type": "ephemeral"}

    system = [
        {
            "type": "text",
            "text": AGENT_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    results: list[ToolResult] = []
    final_text = ""
    try:
        for _ in range(MAX_STEPS):
            resp = client.messages.create(
                model=model,
                max_tokens=1500,
                system=system,
                tools=tools,
                messages=messages,
            )
            final_text = "".join(b.text for b in resp.content if b.type == "text")
            calls = [b for b in resp.content if b.type == "tool_use"]
            if resp.stop_reason != "tool_use" or not calls:
                break
            content_blocks = [d for b in resp.content if (d := _block_to_dict(b)) is not None]
            messages.append({"role": "assistant", "content": content_blocks})
            step_res, step_tool_res, _ = _execute_turn_calls(calls, ctx)
            results.extend(step_res)
            if step_tool_res:
                step_tool_res[-1]["cache_control"] = {"type": "ephemeral"}
            messages.append({"role": "user", "content": step_tool_res})
    except Exception as exc:
        if fake_mode:
            raise AgentUnavailableError(str(exc)) from exc
        return _build_diagnostic_error_tiles(str(exc))

    return _assemble(final_text, results)
