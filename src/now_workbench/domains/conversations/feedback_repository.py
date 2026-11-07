# src/now_workbench/domains/conversations/feedback_repository.py
# Repository for the ratings people give Otto's replies (thumbs up or down, PRD-002).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Feedback repository (schema v15)."""

import sqlite3
from datetime import UTC, datetime

from now_workbench.domains.conversations.models import MessageFeedback, Rating
from now_workbench.platform.db.repository import Repository
from now_workbench.platform.owner import current_owner

__all__ = ["FeedbackRepository"]

_SELECT = """
SELECT f.message_id, m.thread_id, f.owner_email, f.rating, f.comment, m.content AS reply,
       f.created_at, f.updated_at
FROM message_feedback f JOIN chat_messages m ON m.id = f.message_id
"""


def _feedback(row: sqlite3.Row) -> MessageFeedback:
    return MessageFeedback(**{k: row[k] for k in row.keys()})


class FeedbackRepository(Repository):
    """Repository for ``message_feedback``; writes and own reads are owner-scoped."""

    def message_role(self, message_id: str) -> str | None:
        """Return the role of one of the owner's messages, or None when it is not theirs."""
        row = self.conn.execute(
            "SELECT m.role FROM chat_messages m JOIN chat_threads t ON t.id = m.thread_id "
            "WHERE m.id = ? AND t.owner_email = ?;",
            (message_id, current_owner()),
        ).fetchone()
        return str(row["role"]) if row else None

    def put(self, message_id: str, rating: Rating, comment: str) -> bool:
        """Store or replace the owner's rating of one of Otto's replies in their threads.

        Returns:
            False when the message is not an assistant reply in one of the owner's threads.
        """
        now = datetime.now(UTC).isoformat()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO message_feedback (message_id, owner_email, rating, comment, "
                "created_at, updated_at) "
                "SELECT m.id, t.owner_email, ?, ?, ?, ? FROM chat_messages m "
                "JOIN chat_threads t ON t.id = m.thread_id "
                "WHERE m.id = ? AND t.owner_email = ? AND m.role = 'assistant' "
                "ON CONFLICT(message_id) DO UPDATE SET rating = excluded.rating, "
                "comment = excluded.comment, updated_at = excluded.updated_at;",
                (rating, comment, now, now, message_id, current_owner()),
            )
        return cur.rowcount > 0

    def get(self, message_id: str) -> MessageFeedback | None:
        """Return the owner's rating of a reply."""
        row = self.conn.execute(
            f"{_SELECT} WHERE f.message_id = ? AND f.owner_email = ?;",
            (message_id, current_owner()),
        ).fetchone()
        return _feedback(row) if row else None

    def list_own(self) -> list[MessageFeedback]:
        """Return the owner's ratings, most recently changed first."""
        rows = self.conn.execute(
            f"{_SELECT} WHERE f.owner_email = ? ORDER BY f.updated_at DESC, f.message_id;",
            (current_owner(),),
        ).fetchall()
        return [_feedback(r) for r in rows]

    def list_all(self) -> list[MessageFeedback]:
        """Return everyone's ratings, most recently changed first (callers check the role)."""
        rows = self.conn.execute(f"{_SELECT} ORDER BY f.updated_at DESC, f.message_id;").fetchall()
        return [_feedback(r) for r in rows]
