"""Otto agent loop: Async Claude tool-calling over the shared action registry (ADR-011)."""

import functools
import inspect
import sqlite3
from collections.abc import AsyncIterator
from enum import StrEnum
from typing import Any

import anthropic
from pydantic import BaseModel, ConfigDict

from now_workbench.domains.conversations import ChatMessageRecord
from now_workbench.domains.identity import AuthUser, NoActorError
from now_workbench.interfaces.ai.audience import audience_for
from now_workbench.interfaces.ai.conversation import (
    DEFAULT_COMPACT_AT,
    ConversationFiles,
    Question,
    add_usage,
    block_to_dict,
    build_request,
    messages_api,
    messages_for,
    result_content,
    with_question,
)
from now_workbench.interfaces.ai.tiles import (
    AgentStep,
    GenerativeUIResponse,
    TileLayout,
    UITileSpec,
)
from now_workbench.interfaces.ai.tools import execute_tool
from now_workbench.interfaces.ai.tools.base import ToolContext, ToolResult, text_tile

__all__ = [
    "AgentEvent",
    "AgentEventType",
    "AgentUnavailableError",
    "build_diagnostic_error_tiles",
    "ClaudeAgentRunner",
    "make_async_client",
    "make_client",
    "MAX_STEPS",
    "MAX_TILES",
    "run_agent",
]

# Room to detect a problem, fix it and verify the fix within one request.
MAX_STEPS = 12
MAX_TILES = 12


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


@functools.lru_cache(maxsize=2)
def make_client(api_key: str) -> Any:
    """Return the shared synchronous client for a key (one connection pool, reused).

    A new client per request opened a new HTTP pool every time and never closed it. The sync
    client is thread-safe; at most two keys are kept (the current one and a rotated one).
    """
    return anthropic.Anthropic(api_key=api_key)


def make_async_client(api_key: str) -> Any:
    """Create an asynchronous Anthropic client; use it with ``async with`` so it is closed."""
    return anthropic.AsyncAnthropic(api_key=api_key)


def _pick_layout(tiles: list[UITileSpec]) -> TileLayout:
    if len(tiles) <= 1 or any(t.type == "data-table" for t in tiles):
        return "1-col"
    return "2-col" if len(tiles) == 2 else "3-col"


def _assemble(text: str, results: list[ToolResult]) -> GenerativeUIResponse:
    """Merge tool tiles (later results replace earlier tiles with the same id).

    When Otto called `show`, the reply carries the tiles it chose plus any pending
    confirmations; otherwise every tool's tiles, as before (ADR-025).
    """
    if any(r.shown and r.ok for r in results):
        visible = [r for r in results if (r.shown and r.ok) or r.pending]
    else:
        visible = results
    by_id: dict[str, UITileSpec] = {}
    for res in visible:
        for tile in res.tiles:
            by_id.pop(tile.id, None)
            by_id[tile.id] = tile
    tiles = list(by_id.values())[-MAX_TILES:]
    summary = text.strip() or (results[-1].summary if results else "Done.")
    if not tiles:
        tiles = [text_tile("tile-otto-reply", "Otto", summary)]
    steps = [AgentStep(label=r.summary.strip().splitlines()[0][:120], ok=r.ok) for r in results]
    shown = [r for r in results if r.shown and r.ok]
    layout = shown[-1].layout if shown else _pick_layout(tiles)
    ui = [cmd for r in results if r.ok for cmd in r.ui]
    return GenerativeUIResponse(summary=summary, layout=layout, tiles=tiles, steps=steps, ui=ui)


def build_diagnostic_error_tiles(err_msg: str) -> GenerativeUIResponse:
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
    fn = getattr(messages_api(client), "create", None)
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
                "content": result_content(res),
                "is_error": not res.ok,
            }
        )
    return results, tool_results, events


def _actor_or_none(ctx: ToolContext) -> AuthUser | None:
    """The person Otto helps, or None outside a signed-in request (tests, scripts)."""
    try:
        return ctx.actor()
    except NoActorError:
        return None


class _AgentLoop:
    """State of one question's tool loop, shared by the async runner and the sync path.

    The two drivers differ only in how they call the API (awaited or not) and in streaming
    events; message assembly, usage, tool execution and the final reply live here once.
    """

    def __init__(self, question: Question, ctx: ToolContext, model: str) -> None:
        self.ctx = ctx
        self.model = model
        self.compact_at = question.compact_at
        self.messages = (
            with_question(question.prior, question.text, question.files)
            if question.prior is not None
            else messages_for(question.history, question.text, question.files)
        )
        self.start = len(self.messages)
        self.usage: dict[str, int] = {}
        self.results: list[ToolResult] = []
        self.final_text = ""
        self.audience = audience_for(ctx.conn, _actor_or_none(ctx))
        ctx.thread_id = question.thread_id or ctx.thread_id

    def request(self) -> dict[str, Any]:
        """Keyword arguments of the next Messages API call."""
        return build_request(self.model, self.messages, self.compact_at, self.audience)

    def absorb(self, resp: Any) -> list[Any]:
        """Record one response; return the tool calls to run (empty when Otto is done)."""
        add_usage(self.usage, resp)
        self.final_text = "".join(b.text for b in resp.content if b.type == "text")
        blocks = [d for b in resp.content if (d := block_to_dict(b)) is not None]
        self.messages.append({"role": "assistant", "content": blocks})
        calls = [b for b in resp.content if b.type == "tool_use"]
        return calls if resp.stop_reason == "tool_use" else []

    def run_tools(self, calls: list[Any]) -> list[AgentEvent]:
        """Execute the calls, append their results; return the events to stream."""
        step_res, tool_results, events = _execute_turn_calls(calls, self.ctx)
        self.results.extend(step_res)
        self.messages.append({"role": "user", "content": tool_results})
        return events

    @property
    def transcript(self) -> list[dict[str, Any]]:
        """What this run added to the conversation (stored for byte-exact replay)."""
        return self.messages[self.start :]

    def reply(self) -> GenerativeUIResponse:
        """The final reply with usage (the transcript is attached by the caller)."""
        return _assemble(self.final_text, self.results).model_copy(update={"usage": self.usage})


class ClaudeAgentRunner:
    """Async streaming agent runner with Anthropic prompt caching and real-time events."""

    def __init__(
        self,
        client: Any,
        model: str,
        conn: sqlite3.Connection,
        fake_mode: bool = False,
    ) -> None:
        self.client = client
        self.model = model
        self.conn = conn
        self.fake_mode = fake_mode
        self.ctx = ToolContext(conn=conn, fake_mode=fake_mode)

    async def stream_run(
        self,
        user_text: str,
        history: list[ChatMessageRecord],
        files: ConversationFiles | None = None,
        prior: list[dict[str, Any]] | None = None,
        compact_at: int = DEFAULT_COMPACT_AT,
    ) -> AsyncIterator[AgentEvent]:
        """Stream granular lifecycle events through the Claude tool loop.

        Args:
            user_text: The new question.
            history: Earlier messages (used only when ``prior`` is not given).
            files: Attachment blocks for the question (and earlier messages without ``prior``).
            prior: The conversation replayed byte for byte from stored transcripts (ADR-023).
            compact_at: Input size that triggers server-side compaction.
        """
        loop = _AgentLoop(
            Question(user_text, history, files, prior, compact_at), self.ctx, self.model
        )
        try:
            for _ in range(MAX_STEPS):
                calls = loop.absorb(await _call_client_create(self.client, **loop.request()))
                if loop.final_text:
                    yield AgentEvent(
                        event_type=AgentEventType.TEXT_DELTA, payload={"text": loop.final_text}
                    )
                if not calls:
                    break
                for ev in loop.run_tools(calls):
                    yield ev
            yield AgentEvent(
                event_type=AgentEventType.DONE,
                payload={"response": loop.reply().model_dump(), "transcript": loop.transcript},
            )

        except Exception as exc:
            if self.fake_mode:
                raise AgentUnavailableError(str(exc)) from exc
            err_diag = build_diagnostic_error_tiles(str(exc))
            yield AgentEvent(event_type=AgentEventType.ERROR, payload={"error": str(exc)})
            yield AgentEvent(
                event_type=AgentEventType.DONE,
                payload={"response": err_diag.model_dump()},
            )

    async def run(
        self,
        user_text: str,
        history: list[ChatMessageRecord],
        files: ConversationFiles | None = None,
        prior: list[dict[str, Any]] | None = None,
        compact_at: int = DEFAULT_COMPACT_AT,
    ) -> GenerativeUIResponse:
        """Execute the agent run and return the response, with its transcript attached."""
        final_resp: GenerativeUIResponse | None = None
        async for event in self.stream_run(user_text, history, files, prior, compact_at):
            if event.event_type == AgentEventType.DONE:
                raw_resp = event.payload.get("response", {})
                final_resp = GenerativeUIResponse.model_validate(raw_resp).model_copy(
                    update={"transcript": event.payload.get("transcript", [])}
                )
        if final_resp is None:
            return _assemble("No response received from agent.", [])
        return final_resp


def run_agent(
    question: Question,
    conn: sqlite3.Connection,
    client: Any,
    model: str,
    fake_mode: bool = False,
) -> GenerativeUIResponse:
    """Run Otto for one question and return its reply (with transcript and usage).

    Args:
        question: The question and the conversation it continues.
        conn: Open database connection the tools work on.
        client: Anthropic client.
        model: Claude model id.
        fake_mode: Tools simulate instance calls instead of making them.

    Returns:
        Otto's reply with tiles, transcript and token usage.
    """
    import asyncio

    runner = ClaudeAgentRunner(client=client, model=model, conn=conn, fake_mode=fake_mode)

    try:
        asyncio.get_running_loop()
        in_running_loop = True
    except RuntimeError:
        in_running_loop = False

    if in_running_loop:
        return _run_agent_sync(question, conn, client, model, fake_mode)
    q = question
    return asyncio.run(runner.run(q.text, q.history, q.files, q.prior, q.compact_at))


def _run_agent_sync(
    question: Question,
    conn: sqlite3.Connection,
    client: Any,
    model: str,
    fake_mode: bool = False,
) -> GenerativeUIResponse:
    """Direct synchronous runner for tests and sync execution contexts."""
    loop = _AgentLoop(question, ToolContext(conn=conn, fake_mode=fake_mode), model)
    try:
        for _ in range(MAX_STEPS):
            calls = loop.absorb(messages_api(client).create(**loop.request()))
            if not calls:
                break
            loop.run_tools(calls)
    except Exception as exc:
        if fake_mode:
            raise AgentUnavailableError(str(exc)) from exc
        return build_diagnostic_error_tiles(str(exc))
    return loop.reply().model_copy(update={"transcript": loop.transcript})
