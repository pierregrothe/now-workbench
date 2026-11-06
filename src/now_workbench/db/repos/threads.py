"""Thread and chat message repository mixin."""

import json
import sqlite3
import uuid
from datetime import UTC, datetime

from now_workbench.auth.owner import current_owner
from now_workbench.db.models import (
    MAX_THREAD_CONTEXT_MESSAGES,
    ChatMessageRecord,
    ChatThreadCreate,
    ChatThreadRecord,
    ChatThreadUpdate,
)


class ThreadRepositoryMixin:
    """Mixin providing conversational thread and message persistence."""

    conn: sqlite3.Connection

    def list_threads(self, include_archived: bool = True) -> list[ChatThreadRecord]:
        """Return the owner's conversational threads, most recently updated first."""
        where_clause = "WHERE t.owner_email = ?" + (
            "" if include_archived else " AND t.archived = 0"
        )
        cursor = self.conn.execute(
            f"""
            SELECT t.id, t.title, t.archived, t.target_tab, t.created_at, t.updated_at,
                   COUNT(m.id) AS msg_count
            FROM chat_threads t
            LEFT JOIN chat_messages m ON m.thread_id = t.id
            {where_clause}
            GROUP BY t.id
            ORDER BY t.updated_at DESC;
            """,
            (current_owner(),),
        )
        return [
            ChatThreadRecord(
                id=row["id"],
                title=row["title"],
                archived=bool(row["archived"]),
                target_tab=row["target_tab"] or "home",
                message_count=int(row["msg_count"] or 0),
                max_messages=MAX_THREAD_CONTEXT_MESSAGES,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in cursor.fetchall()
        ]

    def get_thread(self, thread_id: str) -> ChatThreadRecord | None:
        """Retrieve one of the owner's threads by ID."""
        cursor = self.conn.execute(
            """
            SELECT t.id, t.title, t.archived, t.target_tab, t.created_at, t.updated_at,
                   COUNT(m.id) AS msg_count
            FROM chat_threads t
            LEFT JOIN chat_messages m ON m.thread_id = t.id
            WHERE t.id = ? AND t.owner_email = ?
            GROUP BY t.id;
            """,
            (thread_id, current_owner()),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return ChatThreadRecord(
            id=row["id"],
            title=row["title"],
            archived=bool(row["archived"]),
            target_tab=row["target_tab"] or "home",
            message_count=int(row["msg_count"] or 0),
            max_messages=MAX_THREAD_CONTEXT_MESSAGES,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create_thread(self, req: ChatThreadCreate) -> ChatThreadRecord:
        """Create or update one of the owner's threads (another owner's id gets a new id)."""
        owner = current_owner()
        thread_id = req.id or f"thread-{uuid.uuid4().hex[:8]}"
        taken = self.conn.execute(
            "SELECT owner_email FROM chat_threads WHERE id = ?;", (thread_id,)
        ).fetchone()
        if taken is not None and taken["owner_email"] != owner:
            thread_id = f"thread-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(UTC).isoformat()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO chat_threads (id, owner_email, title, archived, target_tab,
                                          created_at, updated_at)
                VALUES (?, ?, ?, 0, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    target_tab=excluded.target_tab,
                    updated_at=excluded.updated_at;
                """,
                (thread_id, owner, req.title, req.target_tab, now_iso, now_iso),
            )
        ret = self.get_thread(thread_id)
        assert ret is not None
        return ret

    def update_thread(self, thread_id: str, update: ChatThreadUpdate) -> ChatThreadRecord | None:
        """Update title, archived flag, or target_tab of an existing thread."""
        existing = self.get_thread(thread_id)
        if not existing:
            return None
        new_title = update.title if update.title is not None else existing.title
        new_archived = (
            1 if (update.archived if update.archived is not None else existing.archived) else 0
        )
        new_tab = update.target_tab if update.target_tab is not None else existing.target_tab
        now_iso = datetime.now(UTC).isoformat()
        with self.conn:
            self.conn.execute(
                """
                UPDATE chat_threads
                SET title = ?, archived = ?, target_tab = ?, updated_at = ?
                WHERE id = ? AND owner_email = ?;
                """,
                (new_title, new_archived, new_tab, now_iso, thread_id, current_owner()),
            )
        return self.get_thread(thread_id)

    def delete_thread(self, thread_id: str) -> bool:
        """Delete a conversational thread; its messages cascade (ON DELETE CASCADE)."""
        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM chat_threads WHERE id = ? AND owner_email = ?;",
                (thread_id, current_owner()),
            )
        return cursor.rowcount > 0

    def list_messages(self, thread_id: str) -> list[ChatMessageRecord]:
        """Return all messages in a conversational thread in chronological order."""
        cursor = self.conn.execute(
            """
            SELECT m.id, m.thread_id, m.role, m.content, m.widget_type, m.widget_data,
                   m.created_at
            FROM chat_messages m JOIN chat_threads t ON t.id = m.thread_id
            WHERE m.thread_id = ? AND t.owner_email = ? ORDER BY m.created_at ASC;
            """,
            (thread_id, current_owner()),
        )
        messages: list[ChatMessageRecord] = []
        for row in cursor.fetchall():
            w_data = json.loads(row["widget_data"]) if row["widget_data"] else None
            messages.append(
                ChatMessageRecord(
                    id=row["id"],
                    thread_id=row["thread_id"],
                    role=row["role"],
                    content=row["content"],
                    widget_type=row["widget_type"],
                    widget_data=w_data,
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
            )
        return messages

    def add_message(self, msg: ChatMessageRecord) -> ChatMessageRecord:
        """Persist a chat message in one of the owner's threads and touch its timestamp.

        Raises:
            LookupError: The thread does not exist or belongs to someone else.
        """
        if self.get_thread(msg.thread_id) is None:
            raise LookupError(f"Thread '{msg.thread_id}' not found.")
        w_data_json = json.dumps(msg.widget_data) if msg.widget_data is not None else None
        created_iso = msg.created_at.isoformat()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO chat_messages (id, thread_id, role, content, widget_type,
                                           widget_data, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    msg.id,
                    msg.thread_id,
                    msg.role,
                    msg.content,
                    msg.widget_type,
                    w_data_json,
                    created_iso,
                ),
            )
            self.conn.execute(
                "UPDATE chat_threads SET updated_at = ? WHERE id = ?;",
                (created_iso, msg.thread_id),
            )
        return msg
