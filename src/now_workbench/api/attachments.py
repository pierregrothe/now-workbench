# src/now_workbench/api/attachments.py
# Upload, list and remove files attached to a conversation; the global limits (ADR-021).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Attachments and conversation limits API."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from now_workbench.auth.guard import require_role
from now_workbench.auth.models import AuthUser, Role
from now_workbench.chat.files import (
    LimitReachedError,
    UnsupportedFileError,
    check_can_ask,
    delete_files,
    read_bytes,
    store_attachment,
)
from now_workbench.chat.models import Attachment, ConversationLimits
from now_workbench.db import db_session

__all__ = ["attachments_router", "limits_router"]

attachments_router = APIRouter(prefix="/api/threads", tags=["attachments"])
limits_router = APIRouter(prefix="/api/limits", tags=["limits"])

_MB = 1024 * 1024


async def _read_capped(request: Request, cap: int) -> bytes:
    """Read the body, stopping as soon as it exceeds ``cap`` bytes (never buffer more)."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > cap:
        raise HTTPException(status_code=413, detail=f"Files can be at most {cap // _MB} MB.")
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > cap:
            raise HTTPException(status_code=413, detail=f"Files can be at most {cap // _MB} MB.")
        chunks.append(chunk)
    return b"".join(chunks)


@attachments_router.post("/{thread_id}/attachments", response_model=Attachment)
async def upload_attachment(thread_id: str, filename: str, request: Request) -> Attachment:
    """Attach a file (raw request body) to one of your conversations."""
    with db_session() as repo:
        thread = repo.get_thread(thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail="Thread not found.")
        limits = repo.get_conversation_limits()
        try:
            check_can_ask(thread, repo.list_messages(thread_id), limits)
        except LimitReachedError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    data = await _read_capped(request, limits.max_file_mb * _MB)
    with db_session() as repo:
        try:
            att = store_attachment(
                thread_id, filename, data, repo.list_attachments(thread_id), limits
            )
        except LimitReachedError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        except UnsupportedFileError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc
        return repo.add_attachment(att)


@attachments_router.get("/{thread_id}/attachments", response_model=list[Attachment])
def list_attachments(thread_id: str) -> list[Attachment]:
    """List the files attached to one of your conversations."""
    with db_session() as repo:
        if repo.get_thread(thread_id) is None:
            raise HTTPException(status_code=404, detail="Thread not found.")
        return repo.list_attachments(thread_id)


@attachments_router.get("/{thread_id}/attachments/{attachment_id}")
def download_attachment(thread_id: str, attachment_id: str) -> Response:
    """Return an attachment's bytes (always as a download, never rendered inline)."""
    with db_session() as repo:
        att = repo.get_attachment(attachment_id)
    if att is None or att.thread_id != thread_id:
        raise HTTPException(status_code=404, detail="Attachment not found.")
    return Response(
        read_bytes(att),
        media_type=att.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{att.id}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@attachments_router.delete("/{thread_id}/attachments/{attachment_id}")
def remove_attachment(thread_id: str, attachment_id: str) -> dict[str, bool]:
    """Remove a file you have not sent yet."""
    with db_session() as repo:
        att = repo.get_attachment(attachment_id)
        if att is None or att.thread_id != thread_id:
            raise HTTPException(status_code=404, detail="Attachment not found.")
        if att.message_id is not None:
            raise HTTPException(status_code=409, detail="This file was already sent to Otto.")
        repo.delete_attachment(attachment_id)
    delete_files([att])
    return {"removed": True}


@limits_router.get("", response_model=ConversationLimits)
def get_limits() -> ConversationLimits:
    """Return the conversation limits everyone works under."""
    with db_session() as repo:
        return repo.get_conversation_limits()


@limits_router.put("", response_model=ConversationLimits)
def put_limits(
    limits: ConversationLimits, user: AuthUser = Depends(require_role(Role.ADMIN))
) -> ConversationLimits:
    """Change the conversation limits for everyone (administrators)."""
    with db_session() as repo:
        repo.put_conversation_limits(limits, updated_by=user.email)
        return repo.get_conversation_limits()
