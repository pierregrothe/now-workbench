# src/now_workbench/db/repos/groups.py
# Repository mixin for groups (region, territory, business unit) and their members.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Groups repository mixin (ADR-018)."""

import sqlite3
import uuid
from datetime import UTC, datetime

from now_workbench.db.repos.base import Repository
from now_workbench.sharing.models import (
    Group,
    GroupKind,
    GroupMember,
    MemberRole,
    MemberStatus,
)

__all__ = ["GroupRepository"]

_GROUP_SELECT = """
    SELECT g.id, g.name, g.kind, g.description,
           (SELECT COUNT(*) FROM group_members c
             WHERE c.group_id = g.id AND c.status = 'active') AS member_count,
           m.status AS my_status, m.role AS my_role
    FROM groups g
    LEFT JOIN group_members m ON m.group_id = g.id AND m.email = ?
"""


def _group(row: sqlite3.Row) -> Group:
    return Group(
        id=row["id"],
        name=row["name"],
        kind=GroupKind(row["kind"]),
        description=row["description"],
        member_count=int(row["member_count"]),
        my_status=MemberStatus(row["my_status"]) if row["my_status"] else None,
        my_role=MemberRole(row["my_role"]) if row["my_role"] else None,
    )


def _member(row: sqlite3.Row) -> GroupMember:
    return GroupMember(
        group_id=row["group_id"],
        email=row["email"],
        role=MemberRole(row["role"]),
        status=MemberStatus(row["status"]),
        requested_at=row["requested_at"],
    )


class GroupRepository(Repository):
    """Repository for ``groups`` and ``group_members``; groups are shared, not owner-scoped."""

    def create_group(self, name: str, kind: GroupKind, description: str, created_by: str) -> Group:
        """Create a group.

        Raises:
            ValueError: A group with this name already exists.
        """
        group_id = f"grp-{uuid.uuid4().hex[:8]}"
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO groups (id, name, kind, description, created_by) "
                    "VALUES (?, ?, ?, ?, ?);",
                    (group_id, name, kind.value, description, created_by),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"A group named '{name}' already exists.") from exc
        found = self.get_group(group_id, viewer=created_by)
        assert found is not None
        return found

    def get_group(self, group_id: str, viewer: str) -> Group | None:
        """Return a group with ``viewer``'s standing in it."""
        row = self.conn.execute(f"{_GROUP_SELECT} WHERE g.id = ?;", (viewer, group_id)).fetchone()
        return _group(row) if row else None

    def list_groups(self, viewer: str) -> list[Group]:
        """Return every group (so people can ask to join), by kind then name."""
        rows = self.conn.execute(f"{_GROUP_SELECT} ORDER BY g.kind, g.name;", (viewer,)).fetchall()
        return [_group(r) for r in rows]

    def delete_group(self, group_id: str) -> bool:
        """Delete a group; its members and shares cascade."""
        with self.conn:
            cur = self.conn.execute("DELETE FROM groups WHERE id = ?;", (group_id,))
        return cur.rowcount > 0

    def list_group_members(self, group_id: str) -> list[GroupMember]:
        """Return a group's members and pending requests, pending first."""
        rows = self.conn.execute(
            "SELECT group_id, email, role, status, requested_at FROM group_members "
            "WHERE group_id = ? ORDER BY status DESC, role, email;",
            (group_id,),
        ).fetchall()
        return [_member(r) for r in rows]

    def request_to_join(self, group_id: str, email: str) -> None:
        """Record a pending join request; an existing membership is left unchanged."""
        with self.conn:
            self.conn.execute(
                "INSERT INTO group_members (group_id, email) VALUES (?, ?) "
                "ON CONFLICT(group_id, email) DO NOTHING;",
                (group_id, email),
            )

    def put_group_member(
        self, group_id: str, email: str, role: MemberRole, decided_by: str
    ) -> None:
        """Make ``email`` an active member with ``role`` (accepting any pending request)."""
        now = datetime.now(UTC).isoformat()
        with self.conn:
            self.conn.execute(
                "INSERT INTO group_members (group_id, email, role, status, decided_by, decided_at) "
                "VALUES (?, ?, ?, 'active', ?, ?) ON CONFLICT(group_id, email) DO UPDATE SET "
                "role = excluded.role, status = 'active', decided_by = excluded.decided_by, "
                "decided_at = excluded.decided_at;",
                (group_id, email, role.value, decided_by, now),
            )

    def remove_group_member(self, group_id: str, email: str) -> bool:
        """Remove a member or decline a request."""
        with self.conn:
            cur = self.conn.execute(
                "DELETE FROM group_members WHERE group_id = ? AND email = ?;", (group_id, email)
            )
        return cur.rowcount > 0

    def is_group_admin(self, group_id: str, email: str) -> bool:
        """Return True when ``email`` is an active administrator of the group."""
        row = self.conn.execute(
            "SELECT 1 FROM group_members WHERE group_id = ? AND email = ? "
            "AND role = 'admin' AND status = 'active';",
            (group_id, email),
        ).fetchone()
        return row is not None

    def active_group_ids(self, email: str) -> list[str]:
        """Return the groups ``email`` is an accepted member of."""
        rows = self.conn.execute(
            "SELECT group_id FROM group_members WHERE email = ? AND status = 'active';", (email,)
        ).fetchall()
        return [r["group_id"] for r in rows]

    def administered_group_ids(self, email: str) -> list[str]:
        """Return the groups ``email`` administers."""
        rows = self.conn.execute(
            "SELECT group_id FROM group_members WHERE email = ? AND status = 'active' "
            "AND role = 'admin';",
            (email,),
        ).fetchall()
        return [r["group_id"] for r in rows]

    def pending_join_requests(self, group_ids: list[str] | None) -> list[GroupMember]:
        """Return pending join requests for ``group_ids`` (all groups when None)."""
        sql = (
            "SELECT group_id, email, role, status, requested_at FROM group_members "
            "WHERE status = 'pending'"
        )
        params: list[str] = []
        if group_ids is not None:
            if not group_ids:
                return []
            sql += f" AND group_id IN ({', '.join('?' for _ in group_ids)})"
            params = list(group_ids)
        rows = self.conn.execute(f"{sql} ORDER BY requested_at;", params).fetchall()
        return [_member(r) for r in rows]
