# src/now_workbench/plugins/repository.py
# Plugins recorded per instance (the plugins domain's own repository, ADR-015).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Plugin repository: which plugins the workbench recorded on each instance."""

from datetime import UTC, datetime

from now_workbench.db.repos.base import Repository
from now_workbench.plugins.models import PluginRecord

__all__ = ["PluginRepository"]


class PluginRepository(Repository):
    """Repository for the ``instance_plugins`` table."""

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
