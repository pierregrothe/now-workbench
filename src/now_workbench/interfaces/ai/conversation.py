# src/now_workbench/interfaces/ai/conversation.py
# What Otto sends to Claude: system prompt, byte-exact replay, cache markers, compaction, usage.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Conversation assembly for the Claude API (ADR-023): replay, caching, compaction, billing."""

from dataclasses import dataclass, field
from typing import Any

from now_workbench.domains.conversations import ChatMessageRecord
from now_workbench.interfaces.ai.tools import tool_definitions
from now_workbench.interfaces.ai.tools.base import ToolResult, model_to_text

type FileBlocks = list[dict[str, Any]]

__all__ = [
    "Question",
    "add_usage",
    "AGENT_SYSTEM_PROMPT",
    "block_to_dict",
    "build_request",
    "ConversationFiles",
    "DEFAULT_COMPACT_AT",
    "FileBlocks",
    "messages_api",
    "messages_for",
    "replay_conversation",
    "result_content",
    "with_question",
]


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


def build_request(model: str, messages: list[dict[str, Any]], compact_at: int) -> dict[str, Any]:
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


def messages_api(client: Any) -> Any:
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


def add_usage(total: dict[str, int], resp: Any) -> None:
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


def with_question(
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


def result_content(res: ToolResult) -> str | list[dict[str, Any]]:
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


@dataclass(frozen=True)
class Question:
    """One question to Otto and the conversation it continues.

    Attributes:
        text: What the user asked.
        history: Stored messages of the conversation (used when no transcript exists).
        files: Attachment blocks, earlier and current.
        prior: The stored transcript to replay byte for byte (ADR-023), when there is one.
        compact_at: Input size at which the API compacts the conversation.
    """

    text: str
    history: list[ChatMessageRecord] = field(default_factory=list)
    files: ConversationFiles | None = None
    prior: list[dict[str, Any]] | None = None
    compact_at: int = DEFAULT_COMPACT_AT


def messages_for(
    history: list[ChatMessageRecord], user_text: str, files: ConversationFiles | None
) -> list[dict[str, Any]]:
    if files is None:
        return _history_to_messages(history, user_text)
    return _history_to_messages(history, user_text, files.by_message, files.current)


def block_to_dict(block: Any) -> dict[str, Any] | None:
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
