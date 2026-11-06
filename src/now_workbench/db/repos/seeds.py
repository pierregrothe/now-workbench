"""Seed operation repository mixin."""

import json
import sqlite3

from now_workbench.auth.owner import current_owner
from now_workbench.db.models import (
    SeedOperationRecord,
    SeedRecordItem,
)


class SeedRepositoryMixin:
    """Mixin providing seed operation and rollback persistence."""

    conn: sqlite3.Connection

    def record_seed_operation(self, op: SeedOperationRecord) -> SeedOperationRecord:
        """Persist a completed seed operation audit log."""
        records_json = json.dumps([r.model_dump() for r in op.created_records])
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO seed_operations (id, owner_email, bundle_id, instance_id, status,
                                            created_records, created_at, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    op.id,
                    current_owner(),
                    op.bundle_id,
                    op.instance_id,
                    op.status,
                    records_json,
                    op.created_at,
                    op.error,
                ),
            )
        return op

    def get_seed_operation(self, op_id: str) -> SeedOperationRecord | None:
        """Retrieve a specific seed operation by ID."""
        cursor = self.conn.execute(
            """
            SELECT id, bundle_id, instance_id, status, created_records, created_at, error
            FROM seed_operations WHERE id = ? AND owner_email = ?;
            """,
            (op_id, current_owner()),
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
            error=row["error"],
        )

    def list_seed_operations(self, limit: int = 50) -> list[SeedOperationRecord]:
        """List recent seed operations."""
        cursor = self.conn.execute(
            """
            SELECT id, bundle_id, instance_id, status, created_records, created_at, error
            FROM seed_operations WHERE owner_email = ? ORDER BY created_at DESC LIMIT ?;
            """,
            (current_owner(), limit),
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
                    error=row["error"],
                )
            )
        return ops

    def update_seed_operation_status(self, op_id: str, status: str) -> None:
        """Update status of a seed operation (e.g. rolled_back)."""
        with self.conn:
            self.conn.execute(
                "UPDATE seed_operations SET status = ? WHERE id = ? AND owner_email = ?;",
                (status, op_id, current_owner()),
            )
