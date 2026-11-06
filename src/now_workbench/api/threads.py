"""API routes for conversational threads and persistent message history."""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from now_workbench.ai.actions import execute_autonomous_action
from now_workbench.ai.agent import _build_diagnostic_error_tiles, make_client, run_agent
from now_workbench.ai.tiles import GenerativeUIResponse, resolve_query_to_tiles
from now_workbench.ai.tools import ToolContext, execute_tool
from now_workbench.ai.tools.base import text_tile
from now_workbench.bundles.manager import BundleManager
from now_workbench.config.settings import settings
from now_workbench.connectivity import check_and_record_instance
from now_workbench.db import (
    MAX_THREAD_CONTEXT_MESSAGES,
    ChatMessageCreate,
    ChatMessageRecord,
    ChatThreadCreate,
    ChatThreadRecord,
    ChatThreadUpdate,
    DatabaseRepository,
    db_session,
    get_db_path,
)

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


def _ensure_default_thread(repo: DatabaseRepository) -> list[ChatThreadRecord]:
    """Ensure at least one conversational thread exists on a fresh database."""
    threads = repo.list_threads(include_archived=True)
    if threads:
        return threads

    db_key = str(get_db_path())
    if db_key in _DELETED_DEFAULT_DBS:
        return []

    default_tiles = resolve_query_to_tiles("how many instances do I have")
    thread = repo.create_thread(
        ChatThreadCreate(
            id=DEFAULT_THREAD_ID,
            title="Workspace Orchestration Session",
            target_tab="home",
        )
    )
    repo.add_message(
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
                "context_used": 1,
                "context_limit": MAX_THREAD_CONTEXT_MESSAGES,
            },
        )
    )
    return repo.list_threads(include_archived=True)


def _load_live_bundles_dict() -> list[dict[str, Any]]:
    """Load installed demo bundles as dictionaries for Generative UI tile resolution."""
    manager = BundleManager(settings.bundles_dir)
    result: list[dict[str, Any]] = []
    for info in manager.list_bundles():
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


def _load_verified_instances_dict(repo: DatabaseRepository) -> list[dict[str, Any]]:
    """Load registered instances and verify any with 'unknown' status for real status reporting."""
    instances = repo.list_instances()
    prefs = repo.get_workbench_preferences()
    result: list[dict[str, Any]] = []
    for inst in instances:
        status = inst.status
        if status in ("unknown", ""):
            status, _, _ = check_and_record_instance(
                repo, inst, timeout=1.5, fake_mode=prefs.sdk_fake_mode
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


def _widget_payload(
    resp: GenerativeUIResponse,
    repo: DatabaseRepository,
    history_len: int,
) -> dict[str, Any]:
    """Build persisted widget data for an assistant tile response."""
    active_inst = repo.get_default_instance()
    inst_label = f"{active_inst.name} ({active_inst.url})" if active_inst else "no active instance"
    return {
        "active_instance": inst_label,
        "summary": resp.summary,
        "layout": resp.layout,
        "tiles": [t.model_dump() for t in resp.tiles],
        "steps": [s.model_dump() for s in resp.steps],
        "context_used": min(history_len + 2, MAX_THREAD_CONTEXT_MESSAGES),
        "context_limit": MAX_THREAD_CONTEXT_MESSAGES,
    }


def _agent_reply(
    user_text: str,
    repo: DatabaseRepository,
    history: list[ChatMessageRecord],
) -> tuple[str, str | None, dict[str, Any]] | None:
    """Answer with the Claude tool-calling agent when an API key is configured."""
    api_key = repo.get_decrypted_anthropic_api_key()
    if not api_key:
        return None
    prefs = repo.get_workbench_preferences()
    try:
        resp = run_agent(
            user_text,
            history,
            repo,
            client=make_client(api_key),
            model=prefs.claude_model,
            fake_mode=prefs.sdk_fake_mode,
        )
    except Exception as exc:
        if not prefs.sdk_fake_mode:
            diag_resp = _build_diagnostic_error_tiles(str(exc))
            return (
                diag_resp.summary,
                "generative_tiles",
                _widget_payload(diag_resp, repo, len(history)),
            )
        return None
    return resp.summary, "generative_tiles", _widget_payload(resp, repo, len(history))


def _confirmed_tool_reply(
    req: ChatMessageCreate,
    repo: DatabaseRepository,
    history: list[ChatMessageRecord],
) -> tuple[str, str | None, dict[str, Any]]:
    """Execute a user-confirmed destructive tool call and report the result."""
    data = req.widget_data or {}
    prefs = repo.get_workbench_preferences()
    ctx = ToolContext(repo=repo, fake_mode=prefs.sdk_fake_mode)
    result = execute_tool(ctx, str(data.get("tool", "")), dict(data.get("input") or {}), True)
    tiles = result.tiles or [text_tile("tile-tool-result", "Result", result.summary)]
    resp = GenerativeUIResponse(summary=result.summary, layout=result.layout, tiles=tiles)
    return resp.summary, "generative_tiles", _widget_payload(resp, repo, len(history))


def _build_contextual_reply(
    user_text: str,
    repo: DatabaseRepository,
    history: list[ChatMessageRecord],
) -> tuple[str, str | None, dict[str, Any]]:
    """Determine assistant response text and structured Generative UI tiles with context."""
    agent = _agent_reply(user_text, repo, history)
    if agent is not None:
        return agent

    lower = user_text.lower()
    effective_query = _resolve_effective_query(user_text, history)

    action_resp = execute_autonomous_action(effective_query, repo)
    if action_resp is not None:
        tile_resp = action_resp
    else:
        inst_dicts = _load_verified_instances_dict(repo)
        bundle_dicts = _load_live_bundles_dict()
        tile_resp = resolve_query_to_tiles(
            query=effective_query,
            instances=inst_dicts or None,
            bundles=bundle_dicts or None,
        )

    active_inst = repo.get_default_instance()
    inst_label = f"{active_inst.name} ({active_inst.url})" if active_inst else "no active instance"

    base_widget_data: dict[str, Any] = {
        "active_instance": inst_label,
        "summary": tile_resp.summary,
        "layout": tile_resp.layout,
        "tiles": [t.model_dump() for t in tile_resp.tiles],
        "context_used": min(len(history) + 2, MAX_THREAD_CONTEXT_MESSAGES),
        "context_limit": MAX_THREAD_CONTEXT_MESSAGES,
    }

    if any(kw in lower for kw in ("template", "brand", "customer")):
        return (
            "Configure the customer branding and routing parameters below to generate a "
            "tailored `.sn-demo.zip` bundle:",
            "template_form",
            base_widget_data,
        )
    if any(kw in lower for kw in ("switch", "target")):
        return (
            f"Current target is **{inst_label}**. Select or register a ServiceNow instance below:",
            "instance_selector",
            base_widget_data,
        )
    if any(kw in lower for kw in ("fluent", "schema", "table")):
        return (
            f"{tile_resp.summary} You can inspect `@servicenow/sdk` tables "
            "(`x_snc_ai_triage_log`, `incident`) and compare schema diffs in the "
            "**Fluent Schema** tab or via `workbench demo fluent`.",
            "generative_tiles",
            base_widget_data,
        )
    return (
        f"{tile_resp.summary} (Acknowledged for target **{inst_label}**.)",
        "generative_tiles",
        base_widget_data,
    )


@router.get("", response_model=list[ChatThreadRecord])
def list_threads(include_archived: bool = True) -> list[ChatThreadRecord]:
    """List all conversational threads from SQLite, seeding a default thread if fresh."""
    with db_session() as repo:
        _ensure_default_thread(repo)
        return repo.list_threads(include_archived=include_archived)


@router.post("", response_model=ChatThreadRecord)
def create_thread(req: ChatThreadCreate) -> ChatThreadRecord:
    """Create a new conversational thread in SQLite."""
    with db_session() as repo:
        return repo.create_thread(req)


@router.get("/{thread_id}", response_model=ChatThreadRecord)
def get_thread(thread_id: str) -> ChatThreadRecord:
    """Retrieve metadata and message count for a specific thread."""
    with db_session() as repo:
        thread = repo.get_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found.")
        return thread


@router.patch("/{thread_id}", response_model=ChatThreadRecord)
@router.put("/{thread_id}", response_model=ChatThreadRecord)
def update_thread(thread_id: str, req: ChatThreadUpdate) -> ChatThreadRecord:
    """Update a thread's title, archived state, or target tab in SQLite."""
    with db_session() as repo:
        updated = repo.update_thread(thread_id, req)
        if not updated:
            raise HTTPException(status_code=404, detail="Thread not found.")
        return updated


@router.delete("/{thread_id}")
def delete_thread(thread_id: str) -> dict[str, Any]:
    """Permanently delete a conversational thread and its messages from SQLite."""
    with db_session() as repo:
        deleted = repo.delete_thread(thread_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Thread not found.")
        _DELETED_DEFAULT_DBS.add(str(get_db_path()))
        return {"deleted_thread_id": thread_id, "status": "deleted"}


@router.get("/{thread_id}/messages", response_model=list[ChatMessageRecord])
def list_thread_messages(thread_id: str) -> list[ChatMessageRecord]:
    """Retrieve chronological message history for a conversational thread."""
    with db_session() as repo:
        if thread_id == DEFAULT_THREAD_ID and not repo.get_thread(thread_id):
            _ensure_default_thread(repo)
        elif not repo.get_thread(thread_id):
            raise HTTPException(status_code=404, detail="Thread not found.")
        return repo.list_messages(thread_id)


@router.post("/{thread_id}/messages", response_model=list[ChatMessageRecord])
def post_thread_message(thread_id: str, req: ChatMessageCreate) -> list[ChatMessageRecord]:
    """Append a user message to a thread and generate a contextual assistant reply."""
    with db_session() as repo:
        thread = repo.get_thread(thread_id)
        if thread_id == DEFAULT_THREAD_ID and not thread:
            _ensure_default_thread(repo)
            thread = repo.get_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found.")

        existing_msgs = repo.list_messages(thread_id)
        if len(existing_msgs) >= MAX_THREAD_CONTEXT_MESSAGES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Conversation context limit reached ({MAX_THREAD_CONTEXT_MESSAGES} "
                    "messages max). Please start a new conversation."
                ),
            )

        # Auto-title thread if this is the first user prompt on a generic title
        if req.role == "user" and thread.title in GENERIC_TITLES:
            clean_title = req.content.strip()
            short_title = f"{clean_title[:38]}..." if len(clean_title) > 38 else clean_title
            if short_title:
                repo.update_thread(thread_id, ChatThreadUpdate(title=short_title))

        user_msg = ChatMessageRecord(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            thread_id=thread_id,
            role=req.role,
            content=req.content,
            widget_type=req.widget_type,
            widget_data=req.widget_data,
        )
        repo.add_message(user_msg)

        if req.role == "user":
            context_window = existing_msgs[-MAX_THREAD_CONTEXT_MESSAGES:]
            if req.widget_type == "tool_confirm":
                reply_text, w_type, w_data = _confirmed_tool_reply(req, repo, context_window)
            else:
                reply_text, w_type, w_data = _build_contextual_reply(
                    req.content, repo, context_window
                )
            assistant_msg = ChatMessageRecord(
                id=f"msg-{uuid.uuid4().hex[:8]}",
                thread_id=thread_id,
                role="assistant",
                content=reply_text,
                widget_type=w_type,
                widget_data=w_data,
            )
            repo.add_message(assistant_msg)

        return repo.list_messages(thread_id)
