# src/now_workbench/interfaces/api/replies.py
# Builds Otto's reply to a question: the agent with a key, keyword tiles without one.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Otto reply assembly for conversation threads (ADR-023)."""

import sqlite3
from dataclasses import dataclass
from typing import Any

from now_workbench.domains.bundles import BundleManager
from now_workbench.domains.conversations import (
    ChatMessageCreate,
    ChatMessageRecord,
    ChatRepository,
)
from now_workbench.domains.instances import InstanceRepository, check_and_record_instance
from now_workbench.domains.settings import PreferencesRepository
from now_workbench.domains.sharing import list_accessible
from now_workbench.interfaces.ai.agent import build_diagnostic_error_tiles, make_client, run_agent
from now_workbench.interfaces.ai.conversation import ConversationFiles, Question
from now_workbench.interfaces.ai.tile_routing import resolve_query_to_tiles
from now_workbench.interfaces.ai.tiles import GenerativeUIResponse
from now_workbench.interfaces.ai.tools import execute_tool
from now_workbench.interfaces.ai.tools.base import ToolContext, text_tile

__all__ = ["build_contextual_reply", "confirmed_tool_reply", "load_verified_instances_dict"]


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


def load_verified_instances_dict(conn: sqlite3.Connection) -> list[dict[str, Any]]:
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
        "ui": list(resp.ui),
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
    thread_id: str = "",
) -> _Reply | None:
    """Answer with the Claude tool-calling agent when an API key is configured."""
    pref_repo = PreferencesRepository(conn)
    api_key = pref_repo.get_decrypted_anthropic_api_key()
    if not api_key:
        return None
    prefs = pref_repo.get_workbench_preferences()
    try:
        resp = run_agent(
            Question(
                user_text,
                history,
                files=files,
                prior=prior,
                compact_at=ChatRepository(conn).get_conversation_limits().compact_at_tokens,
                thread_id=thread_id,
            ),
            conn,
            client=make_client(api_key),
            model=prefs.claude_model,
            fake_mode=prefs.sdk_fake_mode,
        )
    except Exception as exc:
        if not prefs.sdk_fake_mode:
            diag_resp = build_diagnostic_error_tiles(str(exc))
            return _Reply(diag_resp.summary, "generative_tiles", _widget_payload(diag_resp, conn))
        return None
    return _Reply(
        resp.summary,
        "generative_tiles",
        _widget_payload(resp, conn),
        transcript=resp.transcript or None,
        tokens=resp.usage.get("billable", 0),
    )


def confirmed_tool_reply(
    req: ChatMessageCreate,
    conn: sqlite3.Connection,
    history: list[ChatMessageRecord],
    thread_id: str = "",
) -> _Reply:
    """Execute a user-confirmed destructive tool call and report the result."""
    data = req.widget_data or {}
    prefs = PreferencesRepository(conn).get_workbench_preferences()
    ctx = ToolContext(conn=conn, fake_mode=prefs.sdk_fake_mode, thread_id=thread_id)
    tool = str(data.get("tool", ""))
    result = execute_tool(ctx, tool, dict(data.get("input") or {}), True)
    tiles = result.tiles or [text_tile("tile-tool-result", "Result", result.summary)]
    resp = GenerativeUIResponse(summary=result.summary, layout=result.layout, tiles=tiles)
    # The person sees the result; Claude, on later questions, also learns which action ran,
    # so Otto never denies or repeats what was done (STORY-059).
    ran = "ran" if result.ok else "tried to run"
    record = f"I {ran} `{tool}` after you confirmed. {result.summary}"
    transcript = [{"role": "assistant", "content": [{"type": "text", "text": record}]}]
    return _Reply(resp.summary, "generative_tiles", _widget_payload(resp, conn), transcript)


def build_contextual_reply(
    user_text: str,
    conn: sqlite3.Connection,
    history: list[ChatMessageRecord],
    files: ConversationFiles | None = None,
    prior: list[dict[str, Any]] | None = None,
    thread_id: str = "",
) -> _Reply:
    """Determine assistant response text and structured Generative UI tiles with context."""
    agent = _agent_reply(user_text, conn, history, files, prior, thread_id)
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

    inst_dicts = load_verified_instances_dict(conn)
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
