"""Otto agent loop: Async Claude tool-calling over the shared action registry (ADR-011)."""

import functools
import inspect
import sqlite3
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import anthropic
from pydantic import BaseModel, ConfigDict

from now_workbench.ai.tiles import AgentStep, GenerativeUIResponse, TileLayout, UITileSpec
from now_workbench.ai.tools import ToolContext, ToolResult, execute_tool, tool_definitions
from now_workbench.ai.tools.base import model_to_text, text_tile
from now_workbench.db import ChatMessageRecord

# Room to detect a problem, fix it and verify the fix within one request.
MAX_STEPS = 12
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
- Work autonomously and check your own work. After an action, verify it with a read-only
  tool (re-evaluate, test the instance, list what was created) and look at any image a tool
  attaches. When something fails or looks wrong, find the cause with read-only tools, fix it
  when the fix is within what was asked and not destructive, then verify again. Report what
  you found and fixed, and say plainly what still does not work and why.
- Never present simulated output as real: if a tool says its result is simulated or could
  not be verified, say so.
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


type FileBlocks = list[dict[str, Any]]


def _as_blocks(content: str | FileBlocks) -> FileBlocks:
    return [{"type": "text", "text": content}] if isinstance(content, str) else content


# Prompt caching and compaction (ADR-023). Tools + system are one stable prefix shared by every
# conversation (1-hour entry); automatic caching moves a 5-minute breakpoint along the
# conversation, which is replayed byte for byte. Compaction summarizes long conversations.
_PREFIX_CACHE: dict[str, str] = {"type": "ephemeral", "ttl": "1h"}
_COMPACT_BETA = "compact-2026-01-12"
DEFAULT_COMPACT_AT = 150_000
_COMPACT_INSTRUCTIONS = (
    "Summarize the transcript inside <summary></summary> tags. Keep what is needed to "
    "continue: the user's goals, the instances, bundles and seed operation ids involved, what "
    "was done and verified, and what is still pending. Do not call any tools while writing "
    "this summary; respond with text only."
)
# Billing weights per token kind (cache reads cost a tenth, writes a quarter more).
_CACHE_READ_WEIGHT = 0.1
_CACHE_WRITE_WEIGHT = 1.25


def _request(model: str, messages: list[dict[str, Any]], compact_at: int) -> dict[str, Any]:
    """Build one Messages API request; identical prefix bytes on every call."""
    return {
        "model": model,
        "max_tokens": 4000,
        "system": [{"type": "text", "text": AGENT_SYSTEM_PROMPT, "cache_control": _PREFIX_CACHE}],
        "tools": sorted(tool_definitions(), key=lambda t: str(t["name"])),
        "messages": list(messages),  # a snapshot: later appends are the next request's
        "cache_control": {"type": "ephemeral"},
        "betas": [_COMPACT_BETA],
        "context_management": {
            "edits": [
                {
                    "type": "compact_20260112",
                    "trigger": {"type": "input_tokens", "value": compact_at},
                    "instructions": _COMPACT_INSTRUCTIONS,
                }
            ]
        },
    }


def _messages_api(client: Any) -> Any:
    """The beta Messages resource (compaction is a beta) when the client has one."""
    beta = getattr(client, "beta", None)
    return getattr(beta, "messages", None) or client.messages


def _usage_counts(resp: Any) -> dict[str, int]:
    """One response's token counts; compaction iterations are part of input and output."""
    usage = getattr(resp, "usage", None)
    if usage is None:
        return {}
    iterations = getattr(usage, "iterations", None) or []
    parts = iterations or [usage]
    return {
        "input": sum(int(getattr(i, "input_tokens", 0) or 0) for i in parts),
        "output": sum(int(getattr(i, "output_tokens", 0) or 0) for i in parts),
        "cache_write": int(getattr(usage, "cache_creation_input_tokens", 0) or 0),
        "cache_read": int(getattr(usage, "cache_read_input_tokens", 0) or 0),
        "compactions": int(any(getattr(i, "type", "") == "compaction" for i in iterations)),
    }


def _add_usage(total: dict[str, int], resp: Any) -> None:
    """Accumulate a response's token usage and the billable total (weights as billed)."""
    for key, value in _usage_counts(resp).items():
        total[key] = total.get(key, 0) + value
    total["billable"] = round(
        total.get("input", 0)
        + total.get("output", 0)
        + _CACHE_WRITE_WEIGHT * total.get("cache_write", 0)
        + _CACHE_READ_WEIGHT * total.get("cache_read", 0)
    )


def replay_conversation(
    history: list[ChatMessageRecord],
    transcripts: dict[str, list[dict[str, Any]]],
    files: dict[str, FileBlocks],
) -> list[dict[str, Any]]:
    """Rebuild a conversation exactly as Claude saw it, for prompt-cache hits (ADR-023).

    Each user message is rebuilt the way it was first sent (its files, then its text); each
    Otto reply is replayed from its stored transcript (tool calls, results, compaction blocks,
    final answer) unchanged. Replies without a transcript (offline answers, confirmations)
    go back as their text. The result is append-only: the same bytes on every later request.

    Args:
        history: The conversation's messages, oldest first.
        transcripts: Stored transcripts by assistant message id.
        files: Attachment content blocks by user message id.

    Returns:
        Messages ready to send before the next question.
    """
    out: list[dict[str, Any]] = []
    for m in history:
        for message in _replayed(m, transcripts, files):
            if out and out[-1]["role"] == message["role"]:
                out[-1] = {
                    "role": message["role"],
                    "content": _join(out[-1]["content"], message["content"]),
                }
            else:
                out.append(message)
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


def _replayed(
    m: ChatMessageRecord,
    transcripts: dict[str, list[dict[str, Any]]],
    files: dict[str, FileBlocks],
) -> list[dict[str, Any]]:
    """The API messages one stored message stands for."""
    if m.role == "user" and (m.content.strip() or files.get(m.id)):
        return [{"role": "user", "content": _content(m.content, files.get(m.id, []))}]
    if m.role == "assistant" and m.id in transcripts:
        return transcripts[m.id]
    if m.role == "assistant" and m.content.strip():
        return [{"role": "assistant", "content": m.content}]
    return []


def _with_question(
    prior: list[dict[str, Any]], user_text: str, files: ConversationFiles | None
) -> list[dict[str, Any]]:
    """The replayed conversation plus the new question (consecutive user turns merge)."""
    question = _content(user_text, files.current if files else [])
    messages = list(prior)
    if messages and messages[-1]["role"] == "user":
        messages[-1] = {"role": "user", "content": _join(messages[-1]["content"], question)}
    else:
        messages.append({"role": "user", "content": question})
    return messages


def _result_content(res: ToolResult) -> str | list[dict[str, Any]]:
    """Tool result text, plus any images the tool attached (sent as image blocks)."""
    text = f"{res.summary}\n{model_to_text(res.data)}"
    if not res.images:
        return text
    images: list[dict[str, Any]] = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg" if data.startswith("/9j/") else "image/png",
                "data": data,
            },
        }
        for data in res.images
    ]
    return [{"type": "text", "text": text}, *images]


def _content(text: str, blocks: FileBlocks) -> str | FileBlocks:
    """Plain text, or the files followed by the text (a text block may not be empty)."""
    if not blocks:
        return text
    return [*blocks, {"type": "text", "text": text.strip() or "(see the attached files)"}]


def _join(previous: str | FileBlocks, content: str | FileBlocks) -> str | FileBlocks:
    """Merge two consecutive same-role contents (the API needs alternating roles)."""
    if isinstance(previous, str) and isinstance(content, str):
        return previous + "\n" + content
    return _as_blocks(previous) + _as_blocks(content)


def _history_to_messages(
    history: list[ChatMessageRecord],
    user_text: str,
    files: dict[str, FileBlocks] | None = None,
    current_files: FileBlocks | None = None,
) -> list[dict[str, Any]]:
    """Convert chat history to alternating Claude messages ending with the new user turn.

    Args:
        history: Earlier messages, oldest first.
        user_text: The new question.
        files: Attachment content blocks per earlier message id (ADR-021).
        current_files: Attachment content blocks sent with the new question.
    """
    files = files or {}
    raw: list[tuple[str, str, FileBlocks]] = [
        (m.role, m.content, files.get(m.id, []))
        for m in history
        if m.role in ("user", "assistant") and (m.content.strip() or files.get(m.id))
    ]
    raw.append(("user", user_text, current_files or []))
    merged: list[dict[str, Any]] = []
    for role, text, blocks in raw:
        content = _content(text, blocks)
        if merged and merged[-1]["role"] == role:
            merged[-1]["content"] = _join(merged[-1]["content"], content)
        else:
            merged.append({"role": role, "content": content})
    while merged and merged[0]["role"] != "user":
        merged.pop(0)
    return merged


@dataclass(frozen=True)
class ConversationFiles:
    """Attachment content blocks for one agent run (ADR-021).

    Attributes:
        by_message: Blocks attached to earlier messages, by message id.
        current: Blocks sent with the new question.
    """

    by_message: dict[str, FileBlocks]
    current: FileBlocks


def _messages_for(
    history: list[ChatMessageRecord], user_text: str, files: ConversationFiles | None
) -> list[dict[str, Any]]:
    if files is None:
        return _history_to_messages(history, user_text)
    return _history_to_messages(history, user_text, files.by_message, files.current)


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
    if block.type == "compaction":
        out: dict[str, Any] = {"type": "compaction", "content": getattr(block, "content", None)}
        if getattr(block, "signature", None):
            out["signature"] = block.signature
        return out
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
    fn = getattr(_messages_api(client), "create", None)
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
                "content": _result_content(res),
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
        messages = (
            _with_question(prior, user_text, files)
            if prior is not None
            else _messages_for(history, user_text, files)
        )
        start = len(messages)
        usage: dict[str, int] = {}
        results: list[ToolResult] = []
        final_text = ""

        try:
            for _ in range(MAX_STEPS):
                resp = await _call_client_create(
                    self.client, **_request(self.model, messages, compact_at)
                )
                _add_usage(usage, resp)
                final_text = "".join(b.text for b in resp.content if b.type == "text")
                if final_text:
                    yield AgentEvent(
                        event_type=AgentEventType.TEXT_DELTA,
                        payload={"text": final_text},
                    )
                blocks = [d for b in resp.content if (d := _block_to_dict(b)) is not None]
                messages.append({"role": "assistant", "content": blocks})
                calls = [b for b in resp.content if b.type == "tool_use"]
                if resp.stop_reason != "tool_use" or not calls:
                    break

                step_res, step_tool_res, step_events = _execute_turn_calls(calls, self.ctx)
                results.extend(step_res)
                for ev in step_events:
                    yield ev
                messages.append({"role": "user", "content": step_tool_res})

            assembled = _assemble(final_text, results).model_copy(update={"usage": usage})
            yield AgentEvent(
                event_type=AgentEventType.DONE,
                payload={"response": assembled.model_dump(), "transcript": messages[start:]},
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
    user_text: str,
    history: list[ChatMessageRecord],
    conn: sqlite3.Connection,
    client: Any,
    model: str,
    fake_mode: bool = False,
    files: ConversationFiles | None = None,
    prior: list[dict[str, Any]] | None = None,
    compact_at: int = DEFAULT_COMPACT_AT,
) -> GenerativeUIResponse:
    """Run Otto for one question and return its reply (with transcript and usage)."""
    import asyncio

    runner = ClaudeAgentRunner(client=client, model=model, conn=conn, fake_mode=fake_mode)

    try:
        asyncio.get_running_loop()
        in_running_loop = True
    except RuntimeError:
        in_running_loop = False

    if in_running_loop:
        return _run_agent_sync(
            user_text, history, conn, client, model, fake_mode, files, prior, compact_at
        )
    return asyncio.run(runner.run(user_text, history, files, prior, compact_at))


def _run_agent_sync(
    user_text: str,
    history: list[ChatMessageRecord],
    conn: sqlite3.Connection,
    client: Any,
    model: str,
    fake_mode: bool = False,
    files: ConversationFiles | None = None,
    prior: list[dict[str, Any]] | None = None,
    compact_at: int = DEFAULT_COMPACT_AT,
) -> GenerativeUIResponse:
    """Direct synchronous runner for tests and sync execution contexts."""
    ctx = ToolContext(conn=conn, fake_mode=fake_mode)
    messages = (
        _with_question(prior, user_text, files)
        if prior is not None
        else _messages_for(history, user_text, files)
    )
    start = len(messages)
    usage: dict[str, int] = {}
    results: list[ToolResult] = []
    final_text = ""
    try:
        for _ in range(MAX_STEPS):
            resp = _messages_api(client).create(**_request(model, messages, compact_at))
            _add_usage(usage, resp)
            final_text = "".join(b.text for b in resp.content if b.type == "text")
            content_blocks = [d for b in resp.content if (d := _block_to_dict(b)) is not None]
            messages.append({"role": "assistant", "content": content_blocks})
            calls = [b for b in resp.content if b.type == "tool_use"]
            if resp.stop_reason != "tool_use" or not calls:
                break
            step_res, step_tool_res, _ = _execute_turn_calls(calls, ctx)
            results.extend(step_res)
            messages.append({"role": "user", "content": step_tool_res})
    except Exception as exc:
        if fake_mode:
            raise AgentUnavailableError(str(exc)) from exc
        return _build_diagnostic_error_tiles(str(exc))

    return _assemble(final_text, results).model_copy(
        update={"usage": usage, "transcript": messages[start:]}
    )
