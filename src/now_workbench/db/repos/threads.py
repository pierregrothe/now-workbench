"""Thread and chat message repository mixin."""

import json
import sqlite3
import uuid
from datetime import UTC, datetime

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
        """Return all conversational threads ordered by most recently updated."""
        where_clause = "" if include_archived else "WHERE t.archived = 0"
        cursor = self.conn.execute(
            f"""
            SELECT t.id, t.title, t.archived, t.target_tab, t.created_at, t.updated_at,
                   COUNT(m.id) AS msg_count
            FROM chat_threads t
            LEFT JOIN chat_messages m ON m.thread_id = t.id
            {where_clause}
            GROUP BY t.id
            ORDER BY t.updated_at DESC;
            """
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
        """Retrieve a specific conversational thread by ID."""
        cursor = self.conn.execute(
            """
            SELECT t.id, t.title, t.archived, t.target_tab, t.created_at, t.updated_at,
                   COUNT(m.id) AS msg_count
            FROM chat_threads t
            LEFT JOIN chat_messages m ON m.thread_id = t.id
            WHERE t.id = ?
            GROUP BY t.id;
            """,
            (thread_id,),
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
        """Create or update a conversational thread."""
        thread_id = req.id or f"thread-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(UTC).isoformat()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO chat_threads (id, title, archived, target_tab, created_at, updated_at)
                VALUES (?, ?, 0, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    target_tab=excluded.target_tab,
                    updated_at=excluded.updated_at;
                """,
                (thread_id, req.title, req.target_tab, now_iso, now_iso),
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
                WHERE id = ?;
                """,
                (new_title, new_archived, new_tab, now_iso, thread_id),
            )
        return self.get_thread(thread_id)

    def delete_thread(self, thread_id: str) -> bool:
        """Delete a conversational thread; its messages cascade (ON DELETE CASCADE)."""
        with self.conn:
            cursor = self.conn.execute("DELETE FROM chat_threads WHERE id = ?;", (thread_id,))
        return cursor.rowcount > 0

    def list_messages(self, thread_id: str) -> list[ChatMessageRecord]:
        """Return all messages in a conversational thread in chronological order."""
        cursor = self.conn.execute(
            """
            SELECT id, thread_id, role, content, widget_type, widget_data, created_at
            FROM chat_messages WHERE thread_id = ? ORDER BY created_at ASC;
            """,
            (thread_id,),
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
        """Persist a chat message and update its thread timestamp."""
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
