"""API routes for conversational threads and persistent message history."""

import asyncio
import contextvars
import json
import logging
import sqlite3
import threading
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from now_workbench.ai.agent import (
    ConversationFiles,
    _build_diagnostic_error_tiles,
    make_client,
    replay_conversation,
    run_agent,
)
from now_workbench.ai.tiles import GenerativeUIResponse, resolve_query_to_tiles
from now_workbench.ai.tools import ToolContext, execute_tool
from now_workbench.ai.tools.base import text_tile
from now_workbench.bundles.manager import BundleManager
from now_workbench.chat.files import (
    LimitReachedError,
    check_can_ask,
    claude_blocks,
    delete_files,
)
from now_workbench.chat.models import Attachment
from now_workbench.connectivity import check_and_record_instance
from now_workbench.db import (
    MAX_THREAD_CONTEXT_MESSAGES,
    ChatMessageCreate,
    ChatMessageRecord,
    ChatThreadCreate,
    ChatThreadRecord,
    ChatThreadUpdate,
    db_session,
    get_db_path,
)
from now_workbench.db.repos.chat import ChatRepository
from now_workbench.db.repos.instances import InstanceRepository
from now_workbench.db.repos.preferences import PreferencesRepository
from now_workbench.db.repos.threads import ThreadRepository
from now_workbench.sharing.access import list_accessible

router = APIRouter(prefix="/api/threads", tags=["threads"])

DEFAULT_THREAD_ID = "default-thread"
DEFAULT_WELCOME = (
    "Welcome to the **ServiceNow Fluent SDK Workbench**. "
    "I can help you switch instances, inspect `*.now.ts` schemas, "
    "apply customer branding templates, or run guided demonstration stages."
)
GENERIC_TITLES = {
    "New Otto Conversation",
    "Workspace Orchestration Session",
    "Zurich Demo & Customization Session",
}
_DELETED_DEFAULT_DBS: set[str] = set()


def _ensure_default_thread(conn: sqlite3.Connection) -> list[ChatThreadRecord]:
    """Ensure at least one conversational thread exists on a fresh database."""
    thread_repo = ThreadRepository(conn)
    threads = thread_repo.list_threads(include_archived=True)
    if threads:
        return threads

    db_key = str(get_db_path())
    if db_key in _DELETED_DEFAULT_DBS:
        return []

    default_tiles = resolve_query_to_tiles("how many instances do I have")
    thread = thread_repo.create_thread(
        ChatThreadCreate(
            id=DEFAULT_THREAD_ID,
            title="Workspace Orchestration Session",
            target_tab="home",
        )
    )
    thread_repo.add_message(
        ChatMessageRecord(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            thread_id=thread.id,
            role="assistant",
            content=DEFAULT_WELCOME,
            widget_type="instance_selector",
            widget_data={
                "summary": default_tiles.summary,
                "layout": default_tiles.layout,
                "tiles": [t.model_dump() for t in default_tiles.tiles],
            },
        )
    )
    return thread_repo.list_threads(include_archived=True)


def _load_live_bundles_dict(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Load the person's own and shared bundles as dictionaries for tile resolution."""
    infos = [BundleManager(a.root).inspect_bundle(a.path) for a in list_accessible(conn)]
    result: list[dict[str, Any]] = []
    for info in infos:
        manifest = info.manifest
        result.append(
            {
                "id": manifest.id,
                "name": manifest.name,
                "industry": manifest.tags[0] if manifest.tags else "Cross-Industry",
                "release": manifest.sn_release,
                "tables_count": max(len(info.fluent_files), 1),
                "records_count": max(len(info.seed_files) * 15, 24),
            }
        )
    return result


def _load_verified_instances_dict(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Load registered instances and verify any with 'unknown' status for real status reporting."""
    instances = InstanceRepository(conn).list_instances()
    prefs = PreferencesRepository(conn).get_workbench_preferences()
    result: list[dict[str, Any]] = []
    for inst in instances:
        status = inst.status
        if status in ("unknown", ""):
            status, _, _ = check_and_record_instance(
                conn, inst, timeout=1.5, fake_mode=prefs.sdk_fake_mode
            )
        result.append(
            {
                "id": inst.id,
                "name": inst.name,
                "url": inst.url,
                "release": inst.release,
                "status": status,
                "is_default": inst.is_default,
            }
        )
    return result


def _resolve_effective_query(user_text: str, history: list[ChatMessageRecord]) -> str:
    """Enrich short follow-up prompts with the latest user message in history."""
    if len(user_text.strip().split()) <= 3 and history:
        last_user_msgs = [m.content for m in history if m.role == "user"]
        if last_user_msgs:
            return f"{user_text} (context: {last_user_msgs[-1]})"
    return user_text


def _widget_payload(resp: GenerativeUIResponse, conn: sqlite3.Connection) -> dict[str, Any]:
    """Build persisted widget data for an assistant tile response."""
    active_inst = InstanceRepository(conn).get_default_instance()
    inst_label = f"{active_inst.name} ({active_inst.url})" if active_inst else "no active instance"
    return {
        "active_instance": inst_label,
        "summary": resp.summary,
        "layout": resp.layout,
        "tiles": [t.model_dump() for t in resp.tiles],
        "steps": [s.model_dump() for s in resp.steps],
        "usage": dict(resp.usage),
    }


@dataclass(frozen=True)
class _Reply:
    """Otto's answer to one message, and what it cost (ADR-023)."""

    text: str
    widget_type: str | None
    widget_data: dict[str, Any]
    transcript: list[dict[str, Any]] | None = None
    tokens: int = 0


def _agent_reply(
    user_text: str,
    conn: sqlite3.Connection,
    history: list[ChatMessageRecord],
    files: ConversationFiles | None = None,
    prior: list[dict[str, Any]] | None = None,
) -> _Reply | None:
    """Answer with the Claude tool-calling agent when an API key is configured."""
    pref_repo = PreferencesRepository(conn)
    api_key = pref_repo.get_decrypted_anthropic_api_key()
    if not api_key:
        return None
    prefs = pref_repo.get_workbench_preferences()
    try:
        resp = run_agent(
            user_text,
            history,
            conn,
            client=make_client(api_key),
            model=prefs.claude_model,
            fake_mode=prefs.sdk_fake_mode,
            files=files,
            prior=prior,
            compact_at=ChatRepository(conn).get_conversation_limits().compact_at_tokens,
        )
    except Exception as exc:
        if not prefs.sdk_fake_mode:
            diag_resp = _build_diagnostic_error_tiles(str(exc))
            return _Reply(diag_resp.summary, "generative_tiles", _widget_payload(diag_resp, conn))
        return None
    return _Reply(
        resp.summary,
        "generative_tiles",
        _widget_payload(resp, conn),
        transcript=resp.transcript or None,
        tokens=resp.usage.get("billable", 0),
    )


def _confirmed_tool_reply(
    req: ChatMessageCreate,
    conn: sqlite3.Connection,
    history: list[ChatMessageRecord],
) -> _Reply:
    """Execute a user-confirmed destructive tool call and report the result."""
    data = req.widget_data or {}
    prefs = PreferencesRepository(conn).get_workbench_preferences()
    ctx = ToolContext(conn=conn, fake_mode=prefs.sdk_fake_mode)
    result = execute_tool(ctx, str(data.get("tool", "")), dict(data.get("input") or {}), True)
    tiles = result.tiles or [text_tile("tile-tool-result", "Result", result.summary)]
    resp = GenerativeUIResponse(summary=result.summary, layout=result.layout, tiles=tiles)
    return _Reply(resp.summary, "generative_tiles", _widget_payload(resp, conn))


def _build_contextual_reply(
    user_text: str,
    conn: sqlite3.Connection,
    history: list[ChatMessageRecord],
    files: ConversationFiles | None = None,
    prior: list[dict[str, Any]] | None = None,
) -> _Reply:
    """Determine assistant response text and structured Generative UI tiles with context."""
    agent = _agent_reply(user_text, conn, history, files, prior)
    if agent is not None:
        return agent
    if files is not None and files.current:
        return _Reply(
            "Otto needs a Claude API key to read attached files. "
            "Ask an administrator to configure one.",
            None,
            {},
        )

    lower = user_text.lower()
    effective_query = _resolve_effective_query(user_text, history)

    inst_dicts = _load_verified_instances_dict(conn)
    bundle_dicts = _load_live_bundles_dict(conn)
    tile_resp = resolve_query_to_tiles(
        query=effective_query,
        instances=inst_dicts or None,
        bundles=bundle_dicts or None,
    )

    active_inst = InstanceRepository(conn).get_default_instance()
    inst_label = f"{active_inst.name} ({active_inst.url})" if active_inst else "no active instance"

    base_widget_data: dict[str, Any] = {
        "active_instance": inst_label,
        "summary": tile_resp.summary,
        "layout": tile_resp.layout,
        "tiles": [t.model_dump() for t in tile_resp.tiles],
    }

    if any(kw in lower for kw in ("template", "brand", "customer")):
        return _Reply(
            "Configure the customer branding and routing parameters below to generate a "
            "tailored `.sn-demo.zip` bundle:",
            "template_form",
            base_widget_data,
        )
    if any(kw in lower for kw in ("switch", "target")):
        return _Reply(
            f"Current target is **{inst_label}**. Select or register a ServiceNow instance below:",
            "instance_selector",
            base_widget_data,
        )
    if any(kw in lower for kw in ("fluent", "schema", "table")):
        return _Reply(
            f"{tile_resp.summary} You can inspect `@servicenow/sdk` tables "
            "(`x_snc_ai_triage_log`, `incident`) and compare schema diffs in the "
            "**Fluent Schema** tab or via `workbench demo fluent`.",
            "generative_tiles",
            base_widget_data,
        )
    return _Reply(
        f"{tile_resp.summary} (Acknowledged for target **{inst_label}**.)",
        "generative_tiles",
        base_widget_data,
    )


@router.get("", response_model=list[ChatThreadRecord])
def list_threads(include_archived: bool = True) -> list[ChatThreadRecord]:
    """List all conversational threads from SQLite, seeding a default thread if fresh."""
    with db_session() as conn:
        _ensure_default_thread(conn)
        return ThreadRepository(conn).list_threads(include_archived=include_archived)


@router.post("", response_model=ChatThreadRecord)
def create_thread(req: ChatThreadCreate) -> ChatThreadRecord:
    """Create a new conversational thread in SQLite."""
    with db_session() as conn:
        return ThreadRepository(conn).create_thread(req)


@router.get("/{thread_id}", response_model=ChatThreadRecord)
def get_thread(thread_id: str) -> ChatThreadRecord:
    """Retrieve metadata and message count for a specific thread."""
    with db_session() as conn:
        thread = ThreadRepository(conn).get_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found.")
        return thread


@router.patch("/{thread_id}", response_model=ChatThreadRecord)
@router.put("/{thread_id}", response_model=ChatThreadRecord)
def update_thread(thread_id: str, req: ChatThreadUpdate) -> ChatThreadRecord:
    """Update a thread's title, archived state, or target tab in SQLite."""
    with db_session() as conn:
        updated = ThreadRepository(conn).update_thread(thread_id, req)
        if not updated:
            raise HTTPException(status_code=404, detail="Thread not found.")
        return updated


@router.delete("/{thread_id}")
def delete_thread(thread_id: str) -> dict[str, Any]:
    """Permanently delete a conversational thread and its messages from SQLite."""
    with db_session() as conn:
        attachments = ChatRepository(conn).list_attachments(thread_id)
        deleted = ThreadRepository(conn).delete_thread(thread_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Thread not found.")
        delete_files(attachments)
        _DELETED_DEFAULT_DBS.add(str(get_db_path()))
        return {"deleted_thread_id": thread_id, "status": "deleted"}


@router.get("/{thread_id}/messages", response_model=list[ChatMessageRecord])
def list_thread_messages(thread_id: str) -> list[ChatMessageRecord]:
    """Retrieve chronological message history for a conversational thread."""
    with db_session() as conn:
        thread_repo = ThreadRepository(conn)
        if thread_id == DEFAULT_THREAD_ID and not thread_repo.get_thread(thread_id):
            _ensure_default_thread(conn)
        elif not thread_repo.get_thread(thread_id):
            raise HTTPException(status_code=404, detail="Thread not found.")
        return thread_repo.list_messages(thread_id)


def _auto_title(conn: sqlite3.Connection, thread: ChatThreadRecord, first_prompt: str) -> None:
    """Name a generically titled thread after its first question."""
    if thread.title not in GENERIC_TITLES:
        return
    clean_title = first_prompt.strip()
    short_title = f"{clean_title[:38]}..." if len(clean_title) > 38 else clean_title
    if short_title:
        ThreadRepository(conn).update_thread(thread.id, ChatThreadUpdate(title=short_title))


def _require_unsent(attachments: list[Attachment], wanted: list[str]) -> None:
    """Refuse ids that are not unsent attachments of this thread."""
    unsent = {a.id for a in attachments if a.message_id is None}
    if any(a not in unsent for a in wanted):
        raise HTTPException(status_code=404, detail="Attachment not found in this thread.")


def _sent_files(attachments: list[Attachment]) -> dict[str, list[dict[str, Any]]]:
    """Claude blocks of every file already sent, by the message that carried it."""
    sent: dict[str, list[dict[str, Any]]] = {}
    for att in attachments:
        if att.message_id is not None:
            sent.setdefault(att.message_id, []).extend(claude_blocks([att]))
    return sent


@router.post("/{thread_id}/messages", response_model=list[ChatMessageRecord])
def post_thread_message(thread_id: str, req: ChatMessageCreate) -> StreamingResponse:
    """Append a user message to a thread and generate a contextual assistant reply.

    Checks (thread, limits, attachments) answer at once with their status codes. The reply
    can take minutes (a full demo pipeline), longer than Cloudflare waits for a response to
    start (100 s, HTTP 524), so the response starts immediately and sends a space every few
    seconds until the thread history, as JSON, follows. Leading whitespace is valid JSON.
    """
    with db_session() as conn:
        chat_repo = ChatRepository(conn)
        thread_repo = ThreadRepository(conn)
        thread = thread_repo.get_thread(thread_id)
        if thread_id == DEFAULT_THREAD_ID and not thread:
            _ensure_default_thread(conn)
            thread = thread_repo.get_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found.")
        existing_msgs = thread_repo.list_messages(thread_id)
        # Confirming an action Otto already proposed is not a new question.
        if req.role == "user" and req.widget_type != "tool_confirm":
            try:
                check_can_ask(thread, chat_repo.get_conversation_limits())
            except LimitReachedError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
        _require_unsent(chat_repo.list_attachments(thread_id), req.attachment_ids)
        if req.role == "user":
            _auto_title(conn, thread, req.content)

    worker = _ReplyWorker(thread_id, req, existing_msgs)
    contextvars.copy_context().run(worker.start)
    return StreamingResponse(worker.stream(), media_type="application/json")


class _ReplyWorker:
    """Saves the message and builds the reply in a thread, keeping the owner scope."""

    def __init__(
        self, thread_id: str, req: ChatMessageCreate, history: list[ChatMessageRecord]
    ) -> None:
        self.thread_id = thread_id
        self.req = req
        self.history = history
        self.result: bytes | None = None
        self._done = threading.Event()

    def start(self) -> None:
        context = contextvars.copy_context()
        threading.Thread(target=context.run, args=(self._run,), daemon=True).start()

    def _run(self) -> None:
        try:
            with db_session() as conn:
                messages = _save_turn(conn, self.thread_id, self.req, self.history)
            payload = [m.model_dump(mode="json") for m in messages]
            self.result = json.dumps(payload).encode()
        except Exception as exc:  # the stream must always end with valid JSON
            logging.getLogger(__name__).exception("Reply failed in thread %s", self.thread_id)
            self.result = json.dumps({"detail": f"Otto could not answer: {exc}"}).encode()
        finally:
            self._done.set()

    async def stream(self) -> AsyncIterator[bytes]:
        while not self._done.is_set():
            await asyncio.to_thread(self._done.wait, _KEEPALIVE_S)
            if not self._done.is_set():
                yield b" "
        yield self.result or b"[]"


_KEEPALIVE_S = 10.0


def _save_turn(
    conn: sqlite3.Connection,
    thread_id: str,
    req: ChatMessageCreate,
    existing_msgs: list[ChatMessageRecord],
) -> list[ChatMessageRecord]:
    """Persist the message, produce Otto's reply for a user turn, and return the history."""
    chat_repo = ChatRepository(conn)
    thread_repo = ThreadRepository(conn)
    attachments = chat_repo.list_attachments(thread_id)
    user_msg = ChatMessageRecord(
        id=f"msg-{uuid.uuid4().hex[:8]}",
        thread_id=thread_id,
        role=req.role,
        content=req.content,
        widget_type=req.widget_type,
        widget_data=req.widget_data,
    )
    thread_repo.add_message(user_msg)
    chat_repo.attach_to_message(req.attachment_ids, user_msg.id)

    if req.role == "user":
        context_window = existing_msgs[-MAX_THREAD_CONTEXT_MESSAGES:]
        if req.widget_type == "tool_confirm":
            reply = _confirmed_tool_reply(req, conn, context_window)
        else:
            by_id = {a.id: a for a in attachments}
            files = ConversationFiles(
                by_message={}, current=claude_blocks([by_id[a] for a in req.attachment_ids])
            )
            prior = replay_conversation(
                existing_msgs, thread_repo.list_transcripts(thread_id), _sent_files(attachments)
            )
            reply = _build_contextual_reply(req.content, conn, context_window, files, prior)
        thread_repo.add_message(
            ChatMessageRecord(
                id=f"msg-{uuid.uuid4().hex[:8]}",
                thread_id=thread_id,
                role="assistant",
                content=reply.text,
                widget_type=reply.widget_type,
                widget_data=reply.widget_data,
            ),
            transcript=reply.transcript,
        )
        thread_repo.add_thread_tokens(thread_id, reply.tokens)
        usage = reply.widget_data.get("usage") or {}
        if usage:
            logging.getLogger("uvicorn.error").info(
                "Otto usage thread=%s input=%s cache_read=%s cache_write=%s output=%s "
                "compactions=%s billable=%s",
                thread_id,
                *(usage.get(k, 0) for k in ("input", "cache_read", "cache_write", "output")),
                usage.get("compactions", 0),
                usage.get("billable", 0),
            )
    return thread_repo.list_messages(thread_id)
