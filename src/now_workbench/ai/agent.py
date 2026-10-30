"""Otto agent loop: Claude tool-calling over the shared action registry."""

from typing import Any

import anthropic

from now_workbench.ai.tiles import GenerativeUIResponse, TileLayout, UITileSpec
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


class AgentUnavailableError(RuntimeError):
    """Raised when the Claude agent cannot run (no key, API failure)."""


def make_client(api_key: str) -> Any:
    """Create a synchronous Anthropic client."""
    return anthropic.Anthropic(api_key=api_key)


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
    return GenerativeUIResponse(summary=summary, layout=_pick_layout(tiles), tiles=tiles)


def run_agent(
    user_text: str,
    history: list[ChatMessageRecord],
    repo: DatabaseRepository,
    client: Any,
    model: str,
    fake_mode: bool = False,
) -> GenerativeUIResponse:
    """Run the tool-calling loop with Anthropic prompt caching and return a tile response."""
    ctx = ToolContext(repo=repo, fake_mode=fake_mode)
    messages = _history_to_messages(history, user_text)
    tools = tool_definitions()
    if tools:
        # Enable Anthropic prompt caching on tool definitions (cache breakpoint 1)
        tools[-1]["cache_control"] = {"type": "ephemeral"}

    # Enable Anthropic prompt caching on the system instructions (cache breakpoint 2)
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
            tool_results: list[dict[str, Any]] = []
            for call in calls:
                res = execute_tool(ctx, call.name, dict(call.input))
                results.append(res)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": call.id,
                        "content": f"{res.summary}\n{model_to_text(res.data)}",
                        "is_error": not res.ok,
                    }
                )
            if tool_results:
                # Cache breakpoint on the latest tool results turn for fast subsequent steps
                tool_results[-1]["cache_control"] = {"type": "ephemeral"}
            messages.append({"role": "user", "content": tool_results})
    except anthropic.APIError as exc:
        raise AgentUnavailableError(str(exc)) from exc
    return _assemble(final_text, results)
