# src/now_workbench/db/repos/artifacts.py
# Repository mixin for artifact ownership, immutable versions and approved shares.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Artifacts repository mixin (ADR-018)."""

import sqlite3
import uuid
from datetime import UTC, datetime

from now_workbench.sharing.models import (
    ArtifactShare,
    ArtifactVersion,
    ShareStatus,
    ShareTarget,
)

__all__ = ["ArtifactRepositoryMixin"]

_SHARE_SELECT = """
    SELECT s.id, s.artifact_id, s.version, s.target, s.group_id, s.status, s.requested_by,
           s.requested_at, s.decided_by, s.decided_at,
           g.name AS group_name, v.name AS artifact_name
    FROM artifact_shares s
    LEFT JOIN groups g ON g.id = s.group_id
    LEFT JOIN artifact_versions v ON v.artifact_id = s.artifact_id AND v.version = s.version
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _version(row: sqlite3.Row) -> ArtifactVersion:
    return ArtifactVersion(
        artifact_id=row["artifact_id"],
        version=int(row["version"]),
        name=row["name"],
        description=row["description"],
        note=row["note"],
        size_bytes=int(row["size_bytes"]),
        created_by=row["created_by"],
        created_at=row["created_at"],
    )


def _share(row: sqlite3.Row) -> ArtifactShare:
    return ArtifactShare(
        id=row["id"],
        artifact_id=row["artifact_id"],
        artifact_name=row["artifact_name"] or row["artifact_id"],
        version=int(row["version"]),
        target=ShareTarget(row["target"]),
        group_id=row["group_id"],
        group_name=row["group_name"],
        status=ShareStatus(row["status"]),
        requested_by=row["requested_by"],
        requested_at=row["requested_at"],
        decided_by=row["decided_by"],
        decided_at=row["decided_at"],
    )


class ArtifactRepositoryMixin:
    """Mixin for ``artifacts``, ``artifact_versions`` and ``artifact_shares``."""

    conn: sqlite3.Connection

    def artifact_owners(self) -> dict[str, str]:
        """Return every registered artifact id with its owner."""
        rows = self.conn.execute("SELECT id, owner_email FROM artifacts;").fetchall()
        return {r["id"]: r["owner_email"] for r in rows}

    def artifact_owner(self, artifact_id: str) -> str | None:
        """Return the owner of an artifact, or None when it is not registered."""
        row = self.conn.execute(
            "SELECT owner_email FROM artifacts WHERE id = ?;", (artifact_id,)
        ).fetchone()
        return str(row["owner_email"]) if row else None

    def register_artifact(self, artifact_id: str, owner: str) -> None:
        """Record who owns a bundle directory (a registered artifact keeps its owner)."""
        with self.conn:
            self.conn.execute(
                "INSERT INTO artifacts (id, owner_email) VALUES (?, ?) ON CONFLICT(id) DO NOTHING;",
                (artifact_id, owner),
            )

    def forget_artifact(self, artifact_id: str) -> None:
        """Remove an artifact's registration; its versions and shares cascade."""
        with self.conn:
            self.conn.execute("DELETE FROM artifacts WHERE id = ?;", (artifact_id,))

    def add_artifact_version(
        self,
        artifact_id: str,
        name: str,
        description: str,
        note: str,
        size_bytes: int,
        created_by: str,
    ) -> ArtifactVersion:
        """Append the next version number for an artifact."""
        with self.conn:
            row = self.conn.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 AS next FROM artifact_versions "
                "WHERE artifact_id = ?;",
                (artifact_id,),
            ).fetchone()
            self.conn.execute(
                "INSERT INTO artifact_versions (artifact_id, version, name, description, note, "
                "size_bytes, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                (
                    artifact_id,
                    int(row["next"]),
                    name,
                    description,
                    note,
                    size_bytes,
                    created_by,
                    _now(),
                ),
            )
        return self.list_artifact_versions(artifact_id)[0]

    def next_artifact_version(self, artifact_id: str) -> int:
        """Return the number the next saved version will get."""
        row = self.conn.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 FROM artifact_versions WHERE artifact_id = ?;",
            (artifact_id,),
        ).fetchone()
        return int(row[0])

    def list_artifact_versions(self, artifact_id: str) -> list[ArtifactVersion]:
        """Return an artifact's versions, newest first."""
        rows = self.conn.execute(
            "SELECT * FROM artifact_versions WHERE artifact_id = ? ORDER BY version DESC;",
            (artifact_id,),
        ).fetchall()
        return [_version(r) for r in rows]

    def get_artifact_version(self, artifact_id: str, version: int) -> ArtifactVersion | None:
        """Return one version."""
        row = self.conn.execute(
            "SELECT * FROM artifact_versions WHERE artifact_id = ? AND version = ?;",
            (artifact_id, version),
        ).fetchone()
        return _version(row) if row else None

    def request_share(
        self,
        artifact_id: str,
        version: int,
        target: ShareTarget,
        group_id: str | None,
        requested_by: str,
    ) -> ArtifactShare:
        """Ask to share a version; an older pending request for the same target is replaced."""
        share_id = f"shr-{uuid.uuid4().hex[:10]}"
        with self.conn:
            self.conn.execute(
                "UPDATE artifact_shares SET status = 'superseded', decided_at = ? "
                "WHERE artifact_id = ? AND target = ? AND group_id IS ? AND status = 'pending';",
                (_now(), artifact_id, target.value, group_id),
            )
            self.conn.execute(
                "INSERT INTO artifact_shares (id, artifact_id, version, target, group_id, "
                "requested_by, requested_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
                (share_id, artifact_id, version, target.value, group_id, requested_by, _now()),
            )
        found = self.get_share(share_id)
        assert found is not None
        return found

    def get_share(self, share_id: str) -> ArtifactShare | None:
        """Return one share."""
        row = self.conn.execute(f"{_SHARE_SELECT} WHERE s.id = ?;", (share_id,)).fetchone()
        return _share(row) if row else None

    def list_artifact_shares(self, artifact_id: str) -> list[ArtifactShare]:
        """Return the live shares of an artifact (pending and approved), newest first."""
        rows = self.conn.execute(
            f"{_SHARE_SELECT} WHERE s.artifact_id = ? AND s.status IN ('pending', 'approved') "
            "ORDER BY s.requested_at DESC;",
            (artifact_id,),
        ).fetchall()
        return [_share(r) for r in rows]

    def decide_share(self, share_id: str, approve: bool, decided_by: str) -> ArtifactShare:
        """Approve or reject a pending share; approval retires the older approved version.

        Raises:
            LookupError: No pending share with this id.
        """
        share = self.get_share(share_id)
        if share is None or share.status is not ShareStatus.PENDING:
            raise LookupError("This share is no longer waiting for a decision.")
        now = _now()
        with self.conn:
            if approve:
                self.conn.execute(
                    "UPDATE artifact_shares SET status = 'superseded' WHERE artifact_id = ? "
                    "AND target = ? AND group_id IS ? AND status = 'approved';",
                    (share.artifact_id, share.target.value, share.group_id),
                )
            self.conn.execute(
                "UPDATE artifact_shares SET status = ?, decided_by = ?, decided_at = ? "
                "WHERE id = ?;",
                ("approved" if approve else "rejected", decided_by, now, share_id),
            )
        decided = self.get_share(share_id)
        assert decided is not None
        return decided

    def withdraw_share(self, share_id: str) -> bool:
        """Delete a share (the owner stops sharing, or withdraws a request)."""
        with self.conn:
            cur = self.conn.execute("DELETE FROM artifact_shares WHERE id = ?;", (share_id,))
        return cur.rowcount > 0

    def pending_shares(self, group_ids: list[str], include_global: bool) -> list[ArtifactShare]:
        """Return pending shares an approver may decide.

        Args:
            group_ids: Groups whose shares the approver decides.
            include_global: Also return shares for everyone (administrators).
        """
        clauses: list[str] = []
        params: list[str] = []
        if group_ids:
            clauses.append(
                f"(s.target = 'group' AND s.group_id IN ({', '.join('?' for _ in group_ids)}))"
            )
            params.extend(group_ids)
        if include_global:
            clauses.append("s.target = 'global'")
        if not clauses:
            return []
        rows = self.conn.execute(
            f"{_SHARE_SELECT} WHERE s.status = 'pending' AND ({' OR '.join(clauses)}) "
            "ORDER BY s.requested_at;",
            params,
        ).fetchall()
        return [_share(r) for r in rows]

    def shared_with(self, email: str, group_ids: list[str]) -> dict[str, int]:
        """Return artifacts shared with ``email`` and the newest version approved for them.

        Their own artifacts are excluded.
        """
        group_clause = (
            f" OR (s.target = 'group' AND s.group_id IN ({', '.join('?' for _ in group_ids)}))"
            if group_ids
            else ""
        )
        rows = self.conn.execute(
            "SELECT s.artifact_id, MAX(s.version) AS version FROM artifact_shares s "
            "JOIN artifacts a ON a.id = s.artifact_id "
            f"WHERE s.status = 'approved' AND a.owner_email != ? "
            f"AND (s.target = 'global'{group_clause}) GROUP BY s.artifact_id;",
            [email, *group_ids],
        ).fetchall()
        return {r["artifact_id"]: int(r["version"]) for r in rows}
