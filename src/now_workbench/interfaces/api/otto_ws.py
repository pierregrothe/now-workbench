# src/now_workbench/interfaces/api/otto_ws.py
# Otto over the /ws/otto WebSocket: allowance check, agent streaming, legacy stream (ADR-011).
# Author: Pierre Grothe
# Date: 2026-11-07
"""WebSocket Otto handlers, moved out of app.py (file-size cap) with the allowance check."""

import sqlite3
import uuid
from typing import Any

from fastapi import WebSocket

from now_workbench.domains.conversations import (
    ChatMessageRecord,
    ChatRepository,
    LimitReachedError,
    ThreadRepository,
    check_can_ask,
)
from now_workbench.domains.settings import PreferencesRepository
from now_workbench.interfaces.ai.agent import (
    AgentEventType,
    ClaudeAgentRunner,
    make_async_client,
    stream_usage_recorder,
)
from now_workbench.interfaces.ai.client import OttoClient
from now_workbench.interfaces.ai.conversation import Question
from now_workbench.interfaces.api.allowance import AllowanceExhaustedError, enforce_allowance
from now_workbench.platform.config.settings import settings
from now_workbench.platform.db.session import db_session

__all__ = ["handle_ws_otto_message"]


def _save_thread_turn(
    conn: sqlite3.Connection, thread_id: str, prompt: str, final_resp: dict[str, Any]
) -> None:
    """Persist completed user prompt and agent response to SQLite thread."""
    thread_repo = ThreadRepository(conn)
    thread_repo.add_message(
        ChatMessageRecord(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            thread_id=thread_id,
            role="user",
            content=prompt,
        )
    )
    thread_repo.add_message(
        ChatMessageRecord(
            id=f"msg-{uuid.uuid4().hex[:8]}",
            thread_id=thread_id,
            role="assistant",
            content=final_resp.get("summary", ""),
            widget_type="generative_tiles",
            widget_data=final_resp,
        )
    )


async def _stream_agent_to_ws(
    websocket: WebSocket,
    runner: ClaudeAgentRunner,
    prompt: str,
    thread_id: str | None,
    conn: sqlite3.Connection,
) -> None:
    """Stream Claude agent lifecycle events to WebSocket and persist to SQLite."""
    thread_repo = ThreadRepository(conn)
    history = thread_repo.list_messages(str(thread_id)) if thread_id else []
    thread = thread_repo.get_thread(str(thread_id)) if thread_id else None
    if thread_id and thread is None:
        await websocket.send_json({"type": "error", "message": "Thread not found."})
        return
    if thread is not None:
        try:
            check_can_ask(thread, ChatRepository(conn).get_conversation_limits())
        except LimitReachedError as exc:
            await websocket.send_json({"type": "error", "message": str(exc)})
            return
    final_resp: dict[str, Any] | None = None
    async for event in runner.stream_run(Question(str(prompt), history)):
        await websocket.send_json({"type": event.event_type.value, **event.payload})
        if event.event_type == AgentEventType.TEXT_DELTA:
            await websocket.send_json({"type": "chunk", "text": event.payload.get("text", "")})
        elif event.event_type == AgentEventType.DONE:
            final_resp = event.payload.get("response")

    if thread_id and final_resp:
        _save_thread_turn(conn, str(thread_id), str(prompt), final_resp)
    await websocket.send_json({"type": "done"})


async def handle_ws_otto_message(websocket: WebSocket, data: dict[str, Any]) -> None:
    """Process a WebSocket Otto chat request with real-time streaming (ADR-011)."""
    prompt = data.get("prompt") or data.get("content")
    thread_id = data.get("thread_id")
    messages = data.get("messages", [])
    context = data.get("context", {})

    with db_session() as conn:
        try:
            note = enforce_allowance(conn)
        except AllowanceExhaustedError as exc:
            await websocket.send_json({"type": "error", "message": str(exc)})
            return
        pref_repo = PreferencesRepository(conn)
        api_key = pref_repo.get_decrypted_anthropic_api_key()
        prefs = pref_repo.get_workbench_preferences()
        active_key = api_key or settings.anthropic_api_key
        model = prefs.claude_model if api_key else settings.claude_model
        fake_mode = prefs.sdk_fake_mode

    if note:
        await websocket.send_json({"type": "usage_warning", "message": note})
    if prompt and active_key:
        async with make_async_client(active_key) as claude:
            with db_session() as conn:
                runner = ClaudeAgentRunner(
                    client=claude, model=model, conn=conn, fake_mode=fake_mode
                )
                await _stream_agent_to_ws(websocket, runner, str(prompt), thread_id, conn)
    else:
        live_client = OttoClient(api_key=active_key, model=model)
        record = stream_usage_recorder(model, str(thread_id or ""))
        try:
            async for chunk in live_client.stream_chat(messages, context=context, on_usage=record):
                await websocket.send_json({"type": "chunk", "text": chunk})
        finally:
            await live_client.aclose()
        await websocket.send_json({"type": "done"})
