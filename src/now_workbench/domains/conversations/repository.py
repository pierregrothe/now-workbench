"""Thread and chat message repository."""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from now_workbench.domains.conversations.models import (
    ChatMessageRecord,
    ChatThreadCreate,
    ChatThreadRecord,
    ChatThreadUpdate,
)
from now_workbench.platform.db.repository import Repository
from now_workbench.platform.owner import current_owner


class ThreadRepository(Repository):
    """Repository for conversational thread and message persistence."""

    def list_threads(self, include_archived: bool = True) -> list[ChatThreadRecord]:
        """Return the owner's conversational threads, most recently updated first."""
        where_clause = "WHERE t.owner_email = ?" + (
            "" if include_archived else " AND t.archived = 0"
        )
        cursor = self.conn.execute(
            f"""
            SELECT t.id, t.title, t.archived, t.target_tab, t.created_at, t.updated_at,
                   t.tokens_used,
                   COALESCE((SELECT json_extract(payload, '$.max_conversation_tokens')
                             FROM app_settings WHERE key = 'conversation_limits'),
                            2000000) AS max_tokens
            FROM chat_threads t
            {where_clause}
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
                tokens_used=int(row["tokens_used"]),
                max_tokens=int(row["max_tokens"]),
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
                   t.tokens_used,
                   COALESCE((SELECT json_extract(payload, '$.max_conversation_tokens')
                             FROM app_settings WHERE key = 'conversation_limits'),
                            2000000) AS max_tokens
            FROM chat_threads t
            WHERE t.id = ? AND t.owner_email = ?;
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
            tokens_used=int(row["tokens_used"]),
            max_tokens=int(row["max_tokens"]),
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

    def add_message(
        self, msg: ChatMessageRecord, transcript: list[dict[str, Any]] | None = None
    ) -> ChatMessageRecord:
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
                                           widget_data, created_at, agent_transcript)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    msg.id,
                    msg.thread_id,
                    msg.role,
                    msg.content,
                    msg.widget_type,
                    w_data_json,
                    created_iso,
                    json.dumps(transcript) if transcript is not None else None,
                ),
            )
            self.conn.execute(
                "UPDATE chat_threads SET updated_at = ? WHERE id = ?;",
                (created_iso, msg.thread_id),
            )
        return msg

    def list_transcripts(self, thread_id: str) -> dict[str, list[dict[str, Any]]]:
        """Return the exact Claude transcript of each assistant reply in one of the owner's threads.

        Replaying these unchanged keeps the conversation prefix byte-identical between
        requests, so Claude serves it from the prompt cache (ADR-023).
        """
        rows = self.conn.execute(
            """
            SELECT m.id, m.agent_transcript FROM chat_messages m
            JOIN chat_threads t ON t.id = m.thread_id
            WHERE m.thread_id = ? AND t.owner_email = ? AND m.agent_transcript IS NOT NULL;
            """,
            (thread_id, current_owner()),
        ).fetchall()
        return {r["id"]: json.loads(r["agent_transcript"]) for r in rows}

    def add_thread_tokens(self, thread_id: str, tokens: int) -> None:
        """Add the tokens a reply used to one of the owner's threads."""
        with self.conn:
            self.conn.execute(
                "UPDATE chat_threads SET tokens_used = tokens_used + ? "
                "WHERE id = ? AND owner_email = ?;",
                (max(0, tokens), thread_id, current_owner()),
            )
