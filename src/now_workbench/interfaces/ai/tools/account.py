# src/now_workbench/interfaces/ai/tools/account.py
# Otto's account tools: the person's profile, their conversations and unsent attachments.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Account tools (ADR-026).

Everything here is the signed-in person's own: repositories are owner-scoped (ADR-018).
A conversation is named by id or title; without one, the tools act on the conversation Otto
is answering in. Uploading files and avatar pictures stays in the interface: the files are
on the person's computer.
"""

from typing import Any

from now_workbench.domains import conversations, profile
from now_workbench.domains.conversations import (
    ChatRepository,
    ChatThreadRecord,
    ChatThreadUpdate,
    ThreadRepository,
)
from now_workbench.domains.profile import PRESET_AVATARS, ProfileRepository
from now_workbench.interfaces.ai.tools.base import (
    ToolContext,
    ToolResult,
    ToolSpec,
    register,
    table_tile,
)
from now_workbench.platform.errors import InvalidInputError

__all__: list[str] = []

_CONVERSATION = {
    "type": "string",
    "description": "Conversation title or id; omit for the current conversation",
}


def _find_conversation(ctx: ToolContext, ref: str | None) -> ChatThreadRecord:
    threads = ThreadRepository(ctx.conn).list_threads(include_archived=True)
    wanted = (ref or ctx.thread_id).strip()
    if not wanted:
        raise InvalidInputError("Say which conversation.")
    exact = [t for t in threads if t.id == wanted or t.title.lower() == wanted.lower()]
    partial = [t for t in threads if wanted.lower() in t.title.lower()]
    found = exact or partial
    if len(found) != 1:
        names = ", ".join(t.title for t in found) or "none"
        raise InvalidInputError(f"No single conversation matches '{wanted}' (candidates: {names}).")
    return found[0]


# --- profile -----------------------------------------------------------------------------


def _show_profile(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    user = ctx.actor()
    record = ProfileRepository(ctx.conn).get_profile(user.email)
    rows = [
        ["Name", record.display_name or "--"],
        ["Email", user.email],
        ["Roles", ", ".join(sorted(r.value for r in user.roles))],
        ["Avatar", record.avatar_preset or record.avatar_kind],
    ]
    return ToolResult(
        summary=f"Profile of {record.display_name or user.email}.",
        data=record.model_dump(),
        tiles=[table_tile("tile-profile", "Your profile", ["Field", "Value"], rows)],
    )


def _update_profile(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    email = ctx.actor().email
    changed = []
    if args.get("display_name") is not None:
        profile.rename(ctx.conn, email, str(args["display_name"]))
        changed.append("name")
    if args.get("avatar_preset"):
        profile.choose_preset_avatar(ctx.conn, email, str(args["avatar_preset"]))
        changed.append("avatar")
    if not changed:
        return ToolResult(
            summary="Nothing to change: give a display_name or an avatar_preset.", ok=False
        )
    return ToolResult(summary=f"Updated your {' and '.join(changed)}.")


# --- conversations -------------------------------------------------------------------------


def _list_conversations(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    threads = ThreadRepository(ctx.conn).list_threads(include_archived=True)
    rows = [
        [
            t.title + (" (this one)" if t.id == ctx.thread_id else ""),
            "archived" if t.archived else "open",
            f"{t.tokens_used}/{t.max_tokens}",
        ]
        for t in threads
    ]
    return ToolResult(
        summary=f"{len(threads)} conversation(s).",
        data={"conversations": [t.model_dump() for t in threads], "current": ctx.thread_id},
        tiles=[
            table_tile("tile-conversations", "Conversations", ["Title", "State", "Tokens"], rows)
        ],
    )


def _rename_conversation(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    thread = _find_conversation(ctx, args.get("conversation"))
    title = str(args["title"]).strip()[:120]
    conversations.update_conversation(ctx.conn, thread.id, ChatThreadUpdate(title=title))
    return ToolResult(summary=f"Renamed '{thread.title}' to '{title}'.")


def _archive_conversation(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    thread = _find_conversation(ctx, args.get("conversation"))
    archived = bool(args.get("archived", True))
    conversations.update_conversation(ctx.conn, thread.id, ChatThreadUpdate(archived=archived))
    return ToolResult(summary=f"{'Archived' if archived else 'Restored'} '{thread.title}'.")


def _delete_conversation(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    thread = _find_conversation(ctx, args.get("conversation"))
    conversations.delete_conversation(ctx.conn, thread.id)
    return ToolResult(summary=f"Deleted '{thread.title}' with its messages and files.")


# --- attachments ---------------------------------------------------------------------------


def _list_attachments(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    thread = _find_conversation(ctx, args.get("conversation"))
    files = ChatRepository(ctx.conn).list_attachments(thread.id)
    rows = [
        [
            a.filename,
            a.media_type,
            f"{a.size_bytes // 1024} KB",
            "sent" if a.message_id else "not sent",
        ]
        for a in files
    ]
    return ToolResult(
        summary=f"{len(files)} file(s) in '{thread.title}'.",
        data={"attachments": [a.model_dump() for a in files]},
        tiles=[
            table_tile(
                "tile-attachments", "Attached files", ["File", "Type", "Size", "State"], rows
            )
        ],
    )


def _remove_attachment(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    thread = _find_conversation(ctx, args.get("conversation"))
    ref = str(args["file"])
    files = ChatRepository(ctx.conn).list_attachments(thread.id)
    match = [a for a in files if ref in (a.id, a.filename)]
    if not match:
        return ToolResult(summary=f"No file '{ref}' in '{thread.title}'.", ok=False)
    conversations.remove_attachment(ctx.conn, thread.id, match[0].id)
    return ToolResult(summary=f"Removed {match[0].filename}.")


register(
    ToolSpec(
        name="show_profile",
        description="Show the person's own profile: name, email, roles, avatar.",
        properties={},
        handler=_show_profile,
        category="account",
    )
)
register(
    ToolSpec(
        name="update_profile",
        description=(
            "Change the person's display name and/or pick a built-in avatar "
            f"({', '.join(PRESET_AVATARS)}). Uploading a picture is done in Settings > Profile."
        ),
        properties={
            "display_name": {"type": "string"},
            "avatar_preset": {"type": "string", "enum": list(PRESET_AVATARS)},
        },
        handler=_update_profile,
        category="account",
    )
)
register(
    ToolSpec(
        name="list_conversations",
        description="List the person's conversations with Otto (open and archived).",
        properties={},
        handler=_list_conversations,
        category="account",
    )
)
register(
    ToolSpec(
        name="rename_conversation",
        description="Rename a conversation (the current one when none is named).",
        properties={"conversation": _CONVERSATION, "title": {"type": "string"}},
        required=["title"],
        handler=_rename_conversation,
        category="account",
    )
)
register(
    ToolSpec(
        name="archive_conversation",
        description="Archive a conversation, or restore it with archived=false.",
        properties={"conversation": _CONVERSATION, "archived": {"type": "boolean"}},
        handler=_archive_conversation,
        category="account",
    )
)
register(
    ToolSpec(
        name="delete_conversation",
        description="Delete a conversation with its messages and attached files.",
        properties={"conversation": _CONVERSATION},
        handler=_delete_conversation,
        category="account",
        destructive=True,
        plan=lambda ctx, a: f"Delete the conversation '{a.get('conversation') or 'this one'}'.",
    )
)
register(
    ToolSpec(
        name="list_attachments",
        description="List files attached to a conversation (the current one by default).",
        properties={"conversation": _CONVERSATION},
        handler=_list_attachments,
        category="account",
    )
)
register(
    ToolSpec(
        name="remove_attachment",
        description=(
            "Remove a file the person attached but has not sent yet. Attaching new files is "
            "done with the paperclip in the chat box."
        ),
        properties={"conversation": _CONVERSATION, "file": {"type": "string"}},
        required=["file"],
        handler=_remove_attachment,
        category="account",
    )
)
