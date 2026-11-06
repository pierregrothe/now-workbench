"""Instance and plugin repository mixin with sealed credentials (ADR-012)."""

import json
import sqlite3
import uuid
from datetime import UTC, datetime

from now_workbench.config.crypto import seal_secret, unseal_secret
from now_workbench.db.models import (
    UNKNOWN_RELEASE,
    InstanceCreate,
    InstanceNode,
    InstanceProfile,
    InstanceRecord,
    InstanceUpdate,
)
from now_workbench.plugins.models import PluginRecord

__all__ = ["InstanceRepositoryMixin", "row_to_instance"]

# The release is never stored on the instance row: it comes from the detected profile.
_SELECT_INSTANCE = f"""
    SELECT i.id, i.name, i.url, i.auth_type, i.credentials_sealed,
           COALESCE(p.release, '{UNKNOWN_RELEASE}') AS release,
           i.purpose, i.is_default, i.status, i.last_checked
    FROM instances i
    LEFT JOIN instance_profiles p ON p.instance_id = i.id
"""

_PROFILE_COLUMNS = (
    "release",
    "build_tag",
    "build_date",
    "platform_name",
    "installation_name",
    "instance_type",
    "production_property",
    "datacenter",
    "db_product",
    "db_version",
    "java_version",
    "os",
)
_NODE_COLUMNS = (
    "node_id",
    "hostname",
    "datacenter",
    "status",
    "cpu_count",
    "memory_max_mb",
    "memory_in_use_mb",
    "memory_pressure",
    "started_at",
)


def _credentials_context(instance_id: str) -> str:
    """Return the GCM binding label tying a credential blob to one instance row."""
    return f"instance:{instance_id}"


def _seal_credentials(instance_id: str, username: str, password: str) -> bytes:
    """Encrypt the username/password pair as one authenticated blob."""
    payload = json.dumps({"username": username, "password": password}, separators=(",", ":"))
    return seal_secret(payload, _credentials_context(instance_id))


def _unseal_credentials(instance_id: str, sealed: bytes) -> tuple[str, str]:
    """Decrypt a credential blob back into ``(username, password)``."""
    data = json.loads(unseal_secret(sealed, _credentials_context(instance_id)))
    return str(data["username"]), str(data["password"])


def _utc_now() -> str:
    """Return the current UTC time in the schema's ISO-8601 ``Z`` format."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def row_to_instance(row: sqlite3.Row) -> InstanceRecord:
    """Convert a SQLite row into an InstanceRecord with decrypted credentials."""
    username, password = _unseal_credentials(row["id"], row["credentials_sealed"])
    return InstanceRecord(
        id=row["id"],
        name=row["name"],
        url=row["url"],
        username=username,
        password=password,
        auth_type=row["auth_type"],
        release=row["release"],
        purpose=row["purpose"],
        is_default=bool(row["is_default"]),
        status=row["status"],
        last_checked=datetime.fromisoformat(row["last_checked"]) if row["last_checked"] else None,
    )


class InstanceRepositoryMixin:
    """Mixin providing instance and plugin persistence methods."""

    conn: sqlite3.Connection

    def list_instances(self) -> list[InstanceRecord]:
        """Return all registered ServiceNow instances, default first."""
        cursor = self.conn.execute(f"{_SELECT_INSTANCE} ORDER BY i.is_default DESC, i.name ASC;")
        return [row_to_instance(row) for row in cursor.fetchall()]

    def get_instance(self, instance_id: str) -> InstanceRecord | None:
        """Fetch an instance by identifier or case-insensitive unique name."""
        row = self.conn.execute(
            f"{_SELECT_INSTANCE} WHERE i.id = ? OR i.name = ? LIMIT 1;",
            (instance_id, instance_id),
        ).fetchone()
        return row_to_instance(row) if row else None

    def get_default_instance(self) -> InstanceRecord | None:
        """Fetch the default instance, promoting the first one by name if none is set."""
        row = self.conn.execute(f"{_SELECT_INSTANCE} WHERE i.is_default = 1;").fetchone()
        if row:
            return row_to_instance(row)
        first = self.conn.execute("SELECT id FROM instances ORDER BY name ASC LIMIT 1;").fetchone()
        if not first:
            return None
        with self.conn:
            self.conn.execute("UPDATE instances SET is_default = 1 WHERE id = ?;", (first["id"],))
        return self.get_instance(first["id"])

    def add_instance(self, inst: InstanceCreate) -> InstanceRecord:
        """Register (or replace by id) an instance in the registry.

        Raises:
            ValueError: Another instance already uses this name.
        """
        inst_id = inst.id or f"inst-{uuid.uuid4().hex[:8]}"
        sealed = _seal_credentials(inst_id, inst.username, inst.password)
        try:
            with self.conn:
                if inst.is_default:
                    self.conn.execute("UPDATE instances SET is_default = 0 WHERE is_default = 1;")
                self.conn.execute(
                    """
                    INSERT INTO instances (id, name, url, auth_type, credentials_sealed,
                                           purpose, is_default)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name = excluded.name,
                        url = excluded.url,
                        auth_type = excluded.auth_type,
                        credentials_sealed = excluded.credentials_sealed,
                        purpose = excluded.purpose,
                        is_default = excluded.is_default,
                        updated_at = excluded.updated_at;
                    """,
                    (
                        inst_id,
                        inst.name,
                        inst.url,
                        inst.auth_type,
                        sealed,
                        inst.purpose,
                        int(inst.is_default),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"An instance named '{inst.name}' already exists.") from exc
        ret = self.get_instance(inst_id)
        assert ret is not None
        return ret

    def set_default_instance(self, instance_id: str) -> bool:
        """Mark a specific instance as the active default."""
        with self.conn:
            if not self.conn.execute(
                "SELECT 1 FROM instances WHERE id = ?;", (instance_id,)
            ).fetchone():
                return False
            self.conn.execute("UPDATE instances SET is_default = 0 WHERE is_default = 1;")
            self.conn.execute("UPDATE instances SET is_default = 1 WHERE id = ?;", (instance_id,))
            return True

    def update_instance_status(self, instance_id: str, status: str) -> None:
        """Update connectivity status and the last_checked timestamp."""
        with self.conn:
            self.conn.execute(
                "UPDATE instances SET status = ?, last_checked = ? WHERE id = ?;",
                (status, datetime.now(UTC).isoformat(), instance_id),
            )

    def save_instance_profile(self, profile: InstanceProfile) -> None:
        """Replace an instance's detected platform profile and node list atomically."""
        values = profile.model_dump(include=set(_PROFILE_COLUMNS))
        if values["production_property"] is not None:
            values["production_property"] = int(values["production_property"])
        cols = ", ".join(_PROFILE_COLUMNS)
        marks = ", ".join("?" for _ in _PROFILE_COLUMNS)
        updates = ", ".join(f"{c} = excluded.{c}" for c in _PROFILE_COLUMNS)
        with self.conn:
            self.conn.execute(
                f"""
                INSERT INTO instance_profiles (instance_id, {cols}, captured_at)
                VALUES (?, {marks}, ?)
                ON CONFLICT(instance_id) DO UPDATE SET {updates},
                    captured_at = excluded.captured_at;
                """,
                (
                    profile.instance_id,
                    *(values[c] for c in _PROFILE_COLUMNS),
                    profile.captured_at.isoformat(),
                ),
            )
            self.conn.execute(
                "DELETE FROM instance_nodes WHERE instance_id = ?;", (profile.instance_id,)
            )
            node_cols = ", ".join(_NODE_COLUMNS)
            node_marks = ", ".join("?" for _ in _NODE_COLUMNS)
            self.conn.executemany(
                f"INSERT INTO instance_nodes (instance_id, {node_cols}) VALUES (?, {node_marks});",
                [
                    (
                        profile.instance_id,
                        *(
                            n.started_at.isoformat()
                            if c == "started_at" and n.started_at
                            else getattr(n, c)
                            for c in _NODE_COLUMNS
                        ),
                    )
                    for n in profile.nodes
                ],
            )

    def get_instance_profile(self, instance_id: str) -> InstanceProfile | None:
        """Return the last detected platform profile (with nodes), or None if never profiled."""
        row = self.conn.execute(
            f"SELECT {', '.join(_PROFILE_COLUMNS)}, captured_at FROM instance_profiles "
            "WHERE instance_id = ?;",
            (instance_id,),
        ).fetchone()
        if row is None:
            return None
        nodes = self.conn.execute(
            f"SELECT {', '.join(_NODE_COLUMNS)} FROM instance_nodes "
            "WHERE instance_id = ? ORDER BY hostname;",
            (instance_id,),
        ).fetchall()
        data = {c: row[c] for c in _PROFILE_COLUMNS}
        if data["production_property"] is not None:
            data["production_property"] = bool(data["production_property"])
        return InstanceProfile(
            instance_id=instance_id,
            captured_at=datetime.fromisoformat(row["captured_at"]),
            nodes=[InstanceNode(**{c: n[c] for c in _NODE_COLUMNS}) for n in nodes],
            **data,
        )

    def update_instance(self, instance_id: str, update: InstanceUpdate) -> InstanceRecord | None:
        """Update an existing instance; credentials are always re-sealed, never plaintext.

        Raises:
            ValueError: The new name collides with another instance.
        """
        existing = self.get_instance(instance_id)
        if not existing:
            return None
        username = update.username if update.username is not None else existing.username
        password = update.password or existing.password
        is_default = update.is_default if update.is_default is not None else existing.is_default
        new_url = update.url if update.url is not None else existing.url
        try:
            with self.conn:
                if is_default:
                    self.conn.execute(
                        "UPDATE instances SET is_default = 0 WHERE is_default = 1 AND id != ?;",
                        (existing.id,),
                    )
                self.conn.execute(
                    """
                    UPDATE instances
                    SET name = ?, url = ?, auth_type = ?, credentials_sealed = ?,
                        purpose = ?, is_default = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (
                        update.name if update.name is not None else existing.name,
                        new_url,
                        update.auth_type if update.auth_type is not None else existing.auth_type,
                        _seal_credentials(existing.id, username, password),
                        update.purpose if update.purpose is not None else existing.purpose,
                        int(is_default),
                        _utc_now(),
                        existing.id,
                    ),
                )
                if new_url != existing.url:
                    # A different endpoint is a different system: its profile is stale.
                    self.conn.execute(
                        "DELETE FROM instance_profiles WHERE instance_id = ?;", (existing.id,)
                    )
                    self.conn.execute(
                        "DELETE FROM instance_nodes WHERE instance_id = ?;", (existing.id,)
                    )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"An instance named '{update.name}' already exists.") from exc
        return self.get_instance(existing.id)

    def delete_instance(self, instance_id: str) -> bool:
        """Remove an instance (its plugins cascade) and re-elect a default if needed."""
        existing = self.get_instance(instance_id)
        if not existing:
            return False
        with self.conn:
            self.conn.execute("DELETE FROM instances WHERE id = ?;", (existing.id,))
            self.conn.execute(
                """
                UPDATE instances SET is_default = 1
                WHERE NOT EXISTS (SELECT 1 FROM instances WHERE is_default = 1)
                  AND id = (SELECT id FROM instances ORDER BY name ASC LIMIT 1);
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
            "SELECT 1 FROM instance_plugins WHERE instance_id = ? AND plugin_id = ? LIMIT 1;",
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
