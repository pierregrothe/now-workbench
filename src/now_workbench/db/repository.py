"""Repository layer providing typed SQLite data access for now-workbench."""

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any, Self

from now_workbench.config.crypto import decrypt_secret, encrypt_secret, mask_api_key
from now_workbench.db.models import (
    MAX_THREAD_CONTEXT_MESSAGES,
    ChatMessageRecord,
    ChatThreadCreate,
    ChatThreadRecord,
    ChatThreadUpdate,
    InstanceCreate,
    InstanceRecord,
    InstanceUpdate,
    SeedOperationRecord,
    SeedRecordItem,
    TemplateRecord,
    WorkbenchPreferences,
    WorkbenchPreferencesUpdate,
)
from now_workbench.plugins.models import PluginRecord


def _row_to_instance(row: sqlite3.Row) -> InstanceRecord:
    """Convert a SQLite row into an InstanceRecord."""
    return InstanceRecord(
        id=row["id"],
        name=row["name"],
        url=row["url"],
        username=row["username"],
        password=decrypt_secret(row["password"]),
        auth_type=row["auth_type"],
        release=row["release"],
        is_default=bool(row["is_default"]),
        status=row["status"],
        last_checked=datetime.fromisoformat(row["last_checked"]) if row["last_checked"] else None,
    )


class DatabaseRepository:
    """Encapsulates SQLite queries for instances, templates, and chats."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self.conn.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    # -- Instances -------------------------------------------------------------
    def list_instances(self) -> list[InstanceRecord]:
        """Return all registered ServiceNow instances."""
        cursor = self.conn.execute(
            """
            SELECT id, name, url, username, password, auth_type, release,
                   is_default, status, last_checked
            FROM instances ORDER BY is_default DESC, name ASC;
            """
        )
        return [_row_to_instance(row) for row in cursor.fetchall()]

    def get_instance(self, instance_id: str) -> InstanceRecord | None:
        """Fetch a specific instance by its identifier or exact name."""
        cursor = self.conn.execute(
            """
            SELECT id, name, url, username, password, auth_type, release,
                   is_default, status, last_checked
            FROM instances WHERE id = ? OR LOWER(name) = LOWER(?);
            """,
            (instance_id, instance_id),
        )
        row = cursor.fetchone()
        return _row_to_instance(row) if row else None

    def get_default_instance(self) -> InstanceRecord | None:
        """Fetch the currently active default instance."""
        cursor = self.conn.execute(
            """
            SELECT id, name, url, username, password, auth_type, release,
                   is_default, status, last_checked
            FROM instances WHERE is_default = 1 LIMIT 1;
            """
        )
        row = cursor.fetchone()
        if not row:
            cursor = self.conn.execute(
                """
                SELECT id, name, url, username, password, auth_type, release,
                       is_default, status, last_checked
                FROM instances ORDER BY name ASC LIMIT 1;
                """
            )
            row = cursor.fetchone()
            if row:
                with self.conn:
                    self.conn.execute(
                        "UPDATE instances SET is_default = 1 WHERE id = ?;",
                        (row["id"],),
                    )
                return self.get_instance(row["id"])
        return _row_to_instance(row) if row else None

    def add_instance(self, inst: InstanceCreate) -> InstanceRecord:
        """Register a new instance into the registry."""
        inst_id = inst.id or f"inst-{uuid.uuid4().hex[:8]}"
        with self.conn:
            if inst.is_default:
                self.conn.execute("UPDATE instances SET is_default = 0;")
            self.conn.execute(
                """
                INSERT INTO instances (id, name, url, username, password, auth_type,
                                       release, is_default, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'unknown')
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    url=excluded.url,
                    username=excluded.username,
                    password=excluded.password,
                    auth_type=excluded.auth_type,
                    release=excluded.release,
                    is_default=excluded.is_default;
                """,
                (
                    inst_id,
                    inst.name,
                    inst.url,
                    inst.username,
                    encrypt_secret(inst.password),
                    inst.auth_type,
                    inst.release,
                    1 if inst.is_default else 0,
                ),
            )
        ret = self.get_instance(inst_id)
        assert ret is not None
        return ret

    def set_default_instance(self, instance_id: str) -> bool:
        """Mark a specific instance as active default."""
        with self.conn:
            cursor = self.conn.execute("SELECT 1 FROM instances WHERE id = ?;", (instance_id,))
            if not cursor.fetchone():
                return False
            self.conn.execute("UPDATE instances SET is_default = 0;")
            self.conn.execute("UPDATE instances SET is_default = 1 WHERE id = ?;", (instance_id,))
            return True

    def update_instance_status(self, instance_id: str, status: str) -> None:
        """Update connectivity status and last_checked timestamp."""
        with self.conn:
            self.conn.execute(
                """
                UPDATE instances
                SET status = ?, last_checked = ?
                WHERE id = ?;
                """,
                (status, datetime.now(UTC).isoformat(), instance_id),
            )

    def update_instance(self, instance_id: str, update: InstanceUpdate) -> InstanceRecord | None:
        """Update an existing instance (rename, endpoint, credentials, release)."""
        existing = self.get_instance(instance_id)
        if not existing:
            return None

        new_name = update.name if update.name is not None else existing.name
        new_url = update.url if update.url is not None else existing.url
        new_user = update.username if update.username is not None else existing.username
        new_pwd = (
            encrypt_secret(update.password)
            if update.password is not None and update.password != ""
            else existing.password
        )
        new_auth = update.auth_type if update.auth_type is not None else existing.auth_type
        new_rel = update.release if update.release is not None else existing.release
        new_def = update.is_default if update.is_default is not None else existing.is_default

        with self.conn:
            if new_def:
                self.conn.execute("UPDATE instances SET is_default = 0;")
            self.conn.execute(
                """
                UPDATE instances
                SET name = ?, url = ?, username = ?, password = ?,
                    auth_type = ?, release = ?, is_default = ?
                WHERE id = ?;
                """,
                (
                    new_name,
                    new_url,
                    new_user,
                    new_pwd,
                    new_auth,
                    new_rel,
                    1 if new_def else 0,
                    existing.id,
                ),
            )
        return self.get_instance(existing.id)

    def delete_instance(self, instance_id: str) -> bool:
        """Remove an instance from the registry."""
        existing = self.get_instance(instance_id)
        if not existing:
            return False

        with self.conn:
            self.conn.execute("DELETE FROM instances WHERE id = ?;", (existing.id,))
            has_default = self.conn.execute(
                "SELECT 1 FROM instances WHERE is_default = 1 LIMIT 1;"
            ).fetchone()
            if not has_default:
                self.conn.execute(
                    """
                    UPDATE instances SET is_default = 1
                    WHERE id = (SELECT id FROM instances ORDER BY name ASC LIMIT 1);
                    """
                )
        return True

    # -- Plugins & Modules -----------------------------------------------------

    def list_instance_plugins(self, instance_id: str) -> list[PluginRecord]:
        """Return all recorded plugins/modules for an instance."""
        rows = self.conn.execute(
            """
            SELECT instance_id, plugin_id, plugin_name, status, installed_at
            FROM instance_plugins
            WHERE instance_id = ?
            ORDER BY plugin_name ASC;
            """,
            (instance_id,),
        ).fetchall()
        return [
            PluginRecord(
                instance_id=r["instance_id"],
                plugin_id=r["plugin_id"],
                plugin_name=r["plugin_name"],
                status=r["status"],
                installed_at=r["installed_at"],
            )
            for r in rows
        ]

    def has_instance_plugin(self, instance_id: str, plugin_id: str) -> bool:
        """Check if an instance has a specific plugin installed."""
        row = self.conn.execute(
            """
            SELECT 1 FROM instance_plugins
            WHERE instance_id = ? AND plugin_id = ?
            LIMIT 1;
            """,
            (instance_id, plugin_id),
        ).fetchone()
        return row is not None

    def add_instance_plugin(
        self,
        instance_id: str,
        plugin_id: str,
        plugin_name: str,
        status: str = "active",
    ) -> PluginRecord:
        """Register or update an installed plugin for an instance."""
        now_ts = datetime.now(UTC).isoformat()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO instance_plugins (
                    instance_id, plugin_id, plugin_name, status, installed_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(instance_id, plugin_id) DO UPDATE SET
                    plugin_name = excluded.plugin_name,
                    status = excluded.status,
                    installed_at = excluded.installed_at;
                """,
                (instance_id, plugin_id, plugin_name, status, now_ts),
            )
        return PluginRecord(
            instance_id=instance_id,
            plugin_id=plugin_id,
            plugin_name=plugin_name,
            status=status,
            installed_at=now_ts,
        )

    # -- Templates -------------------------------------------------------------
    def list_templates(self) -> list[TemplateRecord]:
        """Return all available customization templates."""
        cursor = self.conn.execute(
            """
            SELECT id, name, description, version, base_bundle_id, parameters_schema
            FROM templates;
            """
        )
        templates: list[TemplateRecord] = []
        for row in cursor.fetchall():
            schema = json.loads(row["parameters_schema"]) if row["parameters_schema"] else {}
            templates.append(
                TemplateRecord(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    version=row["version"],
                    base_bundle_id=row["base_bundle_id"],
                    parameters_schema=schema,
                )
            )
        return templates

    def save_template(self, tmpl: TemplateRecord) -> TemplateRecord:
        """Persist or update a customization template."""
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO templates (id, name, description, version, base_bundle_id,
                                       parameters_schema)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    version=excluded.version,
                    base_bundle_id=excluded.base_bundle_id,
                    parameters_schema=excluded.parameters_schema;
                """,
                (
                    tmpl.id,
                    tmpl.name,
                    tmpl.description,
                    tmpl.version,
                    tmpl.base_bundle_id,
                    json.dumps(tmpl.parameters_schema),
                ),
            )
        return tmpl

    # -- Conversational Threads & Messages -------------------------------------
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
        """Delete a conversational thread and all its messages from SQLite."""
        existing = self.get_thread(thread_id)
        if not existing:
            return False
        with self.conn:
            self.conn.execute("DELETE FROM chat_messages WHERE thread_id = ?;", (thread_id,))
            self.conn.execute("DELETE FROM chat_threads WHERE id = ?;", (thread_id,))
        return True

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

    # -- Seed Operations & Rollback -------------------------------------------
    def record_seed_operation(self, op: SeedOperationRecord) -> SeedOperationRecord:
        """Persist a completed seed operation audit log."""
        records_json = json.dumps([r.model_dump() for r in op.created_records])
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO seed_operations (id, bundle_id, instance_id, status,
                                            created_records, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (op.id, op.bundle_id, op.instance_id, op.status, records_json, op.created_at),
            )
        return op

    def get_seed_operation(self, op_id: str) -> SeedOperationRecord | None:
        """Retrieve a specific seed operation by ID."""
        cursor = self.conn.execute(
            """
            SELECT id, bundle_id, instance_id, status, created_records, created_at
            FROM seed_operations WHERE id = ?;
            """,
            (op_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        items = [SeedRecordItem(**it) for it in json.loads(row["created_records"])]
        return SeedOperationRecord(
            id=row["id"],
            bundle_id=row["bundle_id"],
            instance_id=row["instance_id"],
            status=row["status"],
            created_records=items,
            created_at=row["created_at"],
        )

    def list_seed_operations(self, limit: int = 50) -> list[SeedOperationRecord]:
        """List recent seed operations."""
        cursor = self.conn.execute(
            """
            SELECT id, bundle_id, instance_id, status, created_records, created_at
            FROM seed_operations ORDER BY created_at DESC LIMIT ?;
            """,
            (limit,),
        )
        ops: list[SeedOperationRecord] = []
        for row in cursor.fetchall():
            items = [SeedRecordItem(**it) for it in json.loads(row["created_records"])]
            ops.append(
                SeedOperationRecord(
                    id=row["id"],
                    bundle_id=row["bundle_id"],
                    instance_id=row["instance_id"],
                    status=row["status"],
                    created_records=items,
                    created_at=row["created_at"],
                )
            )
        return ops

    def update_seed_operation_status(self, op_id: str, status: str) -> None:
        """Update status of a seed operation (e.g. rolled_back)."""
        with self.conn:
            self.conn.execute(
                "UPDATE seed_operations SET status = ? WHERE id = ?;", (status, op_id)
            )

    # -- Now Workbench Preferences --------------------------------------------
    def _load_raw_preferences_dict(self) -> dict[str, Any]:
        """Load raw stored preferences dictionary from SQLite or initialize encrypted default."""
        cursor = self.conn.execute(
            "SELECT payload FROM workbench_preferences WHERE id = 'default';"
        )
        row = cursor.fetchone()
        if row:
            return dict(json.loads(row["payload"]))

        from now_workbench.config.settings import settings

        raw_key = settings.anthropic_api_key.strip()
        encrypted_key = encrypt_secret(raw_key) if raw_key else ""
        default_prefs = WorkbenchPreferences(
            anthropic_api_key_masked=mask_api_key(raw_key),
            has_anthropic_api_key=bool(raw_key),
            claude_model=settings.claude_model,
        )
        stored = default_prefs.model_dump()
        stored.pop("anthropic_api_key_masked", None)
        stored.pop("has_anthropic_api_key", None)
        stored["anthropic_api_key_encrypted"] = encrypted_key

        with self.conn:
            self.conn.execute(
                """
                INSERT INTO workbench_preferences (id, payload, updated_at)
                VALUES ('default', ?, ?);
                """,
                (json.dumps(stored), default_prefs.updated_at),
            )
        return stored

    def get_decrypted_anthropic_api_key(self) -> str:
        """Decrypt and return the stored Claude AI API key for internal backend use."""
        stored = self._load_raw_preferences_dict()
        enc_val = str(stored.get("anthropic_api_key_encrypted", ""))
        return decrypt_secret(enc_val)

    def get_workbench_preferences(self) -> WorkbenchPreferences:
        """Fetch persisted Now Workbench preferences with masked API key preview."""
        stored = self._load_raw_preferences_dict()
        enc_val = str(stored.pop("anthropic_api_key_encrypted", ""))
        raw_key = decrypt_secret(enc_val)
        stored["anthropic_api_key_masked"] = mask_api_key(raw_key)
        stored["has_anthropic_api_key"] = bool(raw_key)
        return WorkbenchPreferences(**stored)

    def update_workbench_preferences(
        self, update: WorkbenchPreferencesUpdate
    ) -> WorkbenchPreferences:
        """Encrypt secrets and merge partial updates into persisted preferences."""
        stored = self._load_raw_preferences_dict()
        patch_data = update.model_dump(exclude_none=True)

        if "anthropic_api_key" in patch_data:
            new_raw_key = str(patch_data.pop("anthropic_api_key")).strip()
            # Ignore masked preview strings if accidentally echoed back
            if "..." not in new_raw_key:
                if new_raw_key:
                    existing_enc = str(stored.get("anthropic_api_key_encrypted", "")).strip()
                    if existing_enc:
                        raise ValueError(
                            "An active API key exists. You must explicitly delete "
                            "the existing key before setting a new key."
                        )
                    stored["anthropic_api_key_encrypted"] = encrypt_secret(new_raw_key)
                else:
                    stored["anthropic_api_key_encrypted"] = ""

        stored.update(patch_data)
        now_iso = datetime.now(UTC).isoformat()
        stored["updated_at"] = now_iso

        with self.conn:
            self.conn.execute(
                """
                INSERT INTO workbench_preferences (id, payload, updated_at)
                VALUES ('default', ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    payload=excluded.payload,
                    updated_at=excluded.updated_at;
                """,
                (json.dumps(stored), now_iso),
            )
        return self.get_workbench_preferences()

    def delete_anthropic_api_key(self) -> WorkbenchPreferences:
        """Explicitly remove and clear the stored Claude AI API key."""
        stored = self._load_raw_preferences_dict()
        stored["anthropic_api_key_encrypted"] = ""
        now_iso = datetime.now(UTC).isoformat()
        stored["updated_at"] = now_iso
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO workbench_preferences (id, payload, updated_at)
                VALUES ('default', ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    payload=excluded.payload,
                    updated_at=excluded.updated_at;
                """,
                (json.dumps(stored), now_iso),
            )
        return self.get_workbench_preferences()

    def reset_workbench_preferences(self) -> WorkbenchPreferences:
        """Reset Now Workbench preferences to factory defaults."""
        with self.conn:
            self.conn.execute("DELETE FROM workbench_preferences WHERE id = 'default';")
        return self.get_workbench_preferences()
