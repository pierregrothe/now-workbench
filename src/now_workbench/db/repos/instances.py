"""Instance and plugin repository mixin."""

import sqlite3
import uuid
from datetime import UTC, datetime

from now_workbench.config.crypto import decrypt_secret, encrypt_secret
from now_workbench.db.models import (
    InstanceCreate,
    InstanceRecord,
    InstanceUpdate,
)
from now_workbench.plugins.models import PluginRecord


def row_to_instance(row: sqlite3.Row) -> InstanceRecord:
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


class InstanceRepositoryMixin:
    """Mixin providing instance and plugin persistence methods."""

    conn: sqlite3.Connection

    def list_instances(self) -> list[InstanceRecord]:
        """Return all registered ServiceNow instances."""
        cursor = self.conn.execute(
            """
            SELECT id, name, url, username, password, auth_type, release,
                   is_default, status, last_checked
            FROM instances ORDER BY is_default DESC, name ASC;
            """
        )
        return [row_to_instance(row) for row in cursor.fetchall()]

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
        return row_to_instance(row) if row else None

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
        return row_to_instance(row) if row else None

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
