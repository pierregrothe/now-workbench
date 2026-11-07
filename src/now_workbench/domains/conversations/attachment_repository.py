# src/now_workbench/domains/conversations/attachment_repository.py
# Repository mixin for conversation limits and attachment records (ADR-021).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Chat repository."""

import json
import sqlite3
from datetime import UTC, datetime

from now_workbench.domains.conversations.models import Attachment, ConversationLimits
from now_workbench.platform.db.repository import Repository
from now_workbench.platform.owner import current_owner

__all__ = ["ChatRepository"]

_LIMITS_KEY = "conversation_limits"
_COLUMNS = "id, thread_id, filename, media_type, size_bytes, message_id, created_at"


def _attachment(row: sqlite3.Row) -> Attachment:
    return Attachment(**{k: row[k] for k in row.keys()})


class ChatRepository(Repository):
    """Repository for ``app_settings`` (limits) and ``chat_attachments`` (owner-scoped)."""

    def get_conversation_limits(self) -> ConversationLimits:
        """Return the global conversation limits (defaults until an admin changes them)."""
        row = self.conn.execute(
            "SELECT payload FROM app_settings WHERE key = ?;", (_LIMITS_KEY,)
        ).fetchone()
        return (
            ConversationLimits.model_validate_json(row["payload"]) if row else ConversationLimits()
        )

    def put_conversation_limits(self, limits: ConversationLimits, updated_by: str) -> None:
        """Store new global conversation limits."""
        with self.conn:
            self.conn.execute(
                "INSERT INTO app_settings (key, payload, updated_by, updated_at) "
                "VALUES (?, ?, ?, ?) ON CONFLICT(key) DO UPDATE SET payload = excluded.payload, "
                "updated_by = excluded.updated_by, updated_at = excluded.updated_at;",
                (
                    _LIMITS_KEY,
                    json.dumps(limits.model_dump()),
                    updated_by,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def add_attachment(self, att: Attachment) -> Attachment:
        """Record an attachment for one of the owner's threads."""
        with self.conn:
            self.conn.execute(
                "INSERT INTO chat_attachments (id, thread_id, owner_email, filename, media_type, "
                "size_bytes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
                (
                    att.id,
                    att.thread_id,
                    current_owner(),
                    att.filename,
                    att.media_type,
                    att.size_bytes,
                    att.created_at,
                ),
            )
        return att

    def list_attachments(self, thread_id: str) -> list[Attachment]:
        """Return the owner's attachments in a thread, oldest first."""
        rows = self.conn.execute(
            f"SELECT {_COLUMNS} FROM chat_attachments WHERE thread_id = ? AND owner_email = ? "
            "ORDER BY created_at, id;",
            (thread_id, current_owner()),
        ).fetchall()
        return [_attachment(r) for r in rows]

    def get_attachment(self, attachment_id: str) -> Attachment | None:
        """Return one of the owner's attachments."""
        row = self.conn.execute(
            f"SELECT {_COLUMNS} FROM chat_attachments WHERE id = ? AND owner_email = ?;",
            (attachment_id, current_owner()),
        ).fetchone()
        return _attachment(row) if row else None

    def attach_to_message(self, attachment_ids: list[str], message_id: str) -> None:
        """Bind unsent attachments to the message that carries them."""
        with self.conn:
            self.conn.executemany(
                "UPDATE chat_attachments SET message_id = ? WHERE id = ? AND owner_email = ? "
                "AND message_id IS NULL;",
                [(message_id, a, current_owner()) for a in attachment_ids],
            )

    def delete_attachment(self, attachment_id: str) -> bool:
        """Remove an attachment record (the caller removes the file)."""
        with self.conn:
            cur = self.conn.execute(
                "DELETE FROM chat_attachments WHERE id = ? AND owner_email = ?;",
                (attachment_id, current_owner()),
            )
        return cur.rowcount > 0
