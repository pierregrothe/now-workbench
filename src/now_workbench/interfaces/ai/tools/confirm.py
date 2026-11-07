# src/now_workbench/interfaces/ai/tools/confirm.py
# The person confirms a proposed change in words; Otto then runs it (ADR-026).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Conversational confirmation.

A change that removes access or decides for others is proposed first (a pending result with
a Confirm button). The person may click the button, or answer in the conversation. Otto may
then run the proposal only if it is in its latest reply and the person has written since:
a human answer always stands between a proposal and the change, and a proposal runs once.
"""

from typing import Any

from now_workbench.domains.conversations import ChatMessageRecord, ThreadRepository
from now_workbench.interfaces.ai.tools.base import (
    ToolContext,
    ToolResult,
    ToolSpec,
    execute_tool,
    register,
)

__all__: list[str] = []


def _proposals(message: ChatMessageRecord) -> list[dict[str, Any]]:
    """The confirm actions carried by an assistant message's pending tiles."""
    tiles = (message.widget_data or {}).get("tiles") or []
    return [
        act
        for tile in tiles
        if str(tile.get("id", "")).startswith("tile-confirm-")
        for act in (tile.get("props") or {}).get("actions") or []
        if act.get("id") == "confirm_tool"
    ]


def _confirm_action(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    if not ctx.thread_id:
        return ToolResult(summary="There is no conversation to confirm in.", ok=False)
    messages = ThreadRepository(ctx.conn).list_messages(ctx.thread_id)
    last_reply = next(
        (i for i in range(len(messages) - 1, -1, -1) if messages[i].role == "assistant"), None
    )
    if last_reply is None or not any(m.role == "user" for m in messages[last_reply + 1 :]):
        return ToolResult(summary="The person has not answered a proposal yet.", ok=False)
    wanted = args.get("tool")
    proposals = [
        p for p in _proposals(messages[last_reply]) if not wanted or p.get("tool") == wanted
    ]
    if len(proposals) != 1:
        return ToolResult(
            summary="Nothing to confirm: only a change proposed in your last reply can run.",
            ok=False,
        )
    proposal = proposals[0]
    return execute_tool(ctx, str(proposal["tool"]), dict(proposal.get("tool_input") or {}), True)


register(
    ToolSpec(
        name="confirm_action",
        description=(
            "Run the change you proposed in your last reply (the one awaiting confirmation), "
            "after the person clearly agreed in their message (yes, go ahead, do it). Never "
            "call it when they hesitated, asked a question or said no; never call it in the "
            "same reply as the proposal. Give 'tool' when several changes are pending."
        ),
        properties={"tool": {"type": "string", "description": "Name of the proposed tool"}},
        handler=_confirm_action,
        category="confirmation",
    )
)
