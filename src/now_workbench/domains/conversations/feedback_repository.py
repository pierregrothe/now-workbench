# src/now_workbench/domains/conversations/feedback_repository.py
# Repository for the ratings people give Otto's replies (thumbs up or down, PRD-002).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Feedback repository (schema v15).

A rating has no owner column of its own: it belongs to whoever owns the conversation, read
through ``chat_threads``, so it moves with the thread (for example when orphans are claimed).
"""

import sqlite3
from datetime import UTC, datetime

from now_workbench.domains.conversations.models import (
    MAX_FEEDBACK_LISTED,
    MessageFeedback,
    Rating,
)
from now_workbench.platform.db.repository import Repository
from now_workbench.platform.owner import current_owner

__all__ = ["FeedbackRepository"]

_SELECT = """
SELECT f.message_id, m.thread_id, t.owner_email, f.rating, f.comment, m.content AS reply,
       f.created_at, f.updated_at
FROM message_feedback f
JOIN chat_messages m ON m.id = f.message_id
JOIN chat_threads t ON t.id = m.thread_id
"""
_NEWEST = f"ORDER BY f.updated_at DESC, f.message_id LIMIT {MAX_FEEDBACK_LISTED}"


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

    def put(self, message_id: str, rating: Rating, comment: str | None) -> MessageFeedback | None:
        """Store or replace the owner's rating of one of Otto's replies in their threads.

        Args:
            message_id: The assistant message to rate.
            rating: "up" or "down".
            comment: The new comment ("" clears it); None keeps the stored one.

        Returns:
            The stored rating, or None when the message is not an assistant reply in one of
            the owner's threads.
        """
        now = datetime.now(UTC).isoformat()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO message_feedback (message_id, rating, comment, created_at, "
                "updated_at) "
                "SELECT m.id, ?, COALESCE(?, ''), ?, ? FROM chat_messages m "
                "JOIN chat_threads t ON t.id = m.thread_id "
                "WHERE m.id = ? AND t.owner_email = ? AND m.role = 'assistant' "
                "ON CONFLICT(message_id) DO UPDATE SET rating = excluded.rating, "
                "comment = COALESCE(?, message_feedback.comment), "
                "updated_at = excluded.updated_at;",
                (rating, comment, now, now, message_id, current_owner(), comment),
            )
        return self.get(message_id) if cur.rowcount > 0 else None

    def get(self, message_id: str) -> MessageFeedback | None:
        """Return the owner's rating of a reply."""
        row = self.conn.execute(
            f"{_SELECT} WHERE f.message_id = ? AND t.owner_email = ?;",
            (message_id, current_owner()),
        ).fetchone()
        return _feedback(row) if row else None

    def list_own(self) -> list[MessageFeedback]:
        """Return the owner's newest ratings (at most ``MAX_FEEDBACK_LISTED``)."""
        rows = self.conn.execute(
            f"{_SELECT} WHERE t.owner_email = ? {_NEWEST};", (current_owner(),)
        ).fetchall()
        return [_feedback(r) for r in rows]

    def list_all(self) -> list[MessageFeedback]:
        """Return everyone's newest ratings (callers check the role)."""
        rows = self.conn.execute(f"{_SELECT} {_NEWEST};").fetchall()
        return [_feedback(r) for r in rows]
