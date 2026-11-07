# src/now_workbench/domains/conversations/service.py
# Managing one's own conversations and their unsent attachments (shared by the API and Otto).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Conversation service (ADR-021, ADR-026). Repositories are owner-scoped (ADR-018)."""

import sqlite3

from now_workbench.domains.conversations.attachment_repository import ChatRepository
from now_workbench.domains.conversations.files import delete_files
from now_workbench.domains.conversations.models import ChatThreadRecord, ChatThreadUpdate
from now_workbench.domains.conversations.repository import ThreadRepository
from now_workbench.platform.errors import ConflictError, NotFoundError

__all__ = ["delete_conversation", "remove_attachment", "update_conversation"]


def update_conversation(
    conn: sqlite3.Connection, thread_id: str, update: ChatThreadUpdate
) -> ChatThreadRecord:
    """Rename, archive or restore a conversation."""
    updated = ThreadRepository(conn).update_thread(thread_id, update)
    if not updated:
        raise NotFoundError("Thread not found.")
    return updated


def delete_conversation(conn: sqlite3.Connection, thread_id: str) -> None:
    """Delete a conversation, its messages and its attached files."""
    attachments = ChatRepository(conn).list_attachments(thread_id)
    if not ThreadRepository(conn).delete_thread(thread_id):
        raise NotFoundError("Thread not found.")
    delete_files(attachments)


def remove_attachment(conn: sqlite3.Connection, thread_id: str, attachment_id: str) -> None:
    """Remove a file not yet sent to Otto.

    Raises:
        NotFoundError: No such attachment in this conversation.
        ConflictError: The file was already sent.
    """
    chat = ChatRepository(conn)
    att = chat.get_attachment(attachment_id)
    if att is None or att.thread_id != thread_id:
        raise NotFoundError("Attachment not found.")
    if att.message_id is not None:
        raise ConflictError("This file was already sent to Otto.")
    chat.delete_attachment(attachment_id)
    delete_files([att])
