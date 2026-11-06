# src/now_workbench/db/repos/users.py
# Repository mixin for the people allowed into the workbench and their roles.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Users repository mixin (ADR-017)."""

import sqlite3
from datetime import UTC, datetime

from now_workbench.auth.models import Role, TeamMember

__all__ = ["UserRepositoryMixin"]


def _roles(row: sqlite3.Row) -> frozenset[Role]:
    roles: set[Role] = set()
    if row["is_admin"]:
        roles.add(Role.ADMIN)
    if row["is_consultant"]:
        roles.add(Role.SOLUTION_CONSULTANT)
    return frozenset(roles)


class UserRepositoryMixin:
    """Mixin for the ``users`` table."""

    conn: sqlite3.Connection

    def get_user_roles(self, email: str) -> frozenset[Role]:
        """Return the roles of an email (empty when it is not a member)."""
        row = self.conn.execute(
            "SELECT is_admin, is_consultant FROM users WHERE email = ?;", (email,)
        ).fetchone()
        return _roles(row) if row else frozenset()

    def count_admins(self) -> int:
        """Return how many members hold the admin role."""
        return int(
            self.conn.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1;").fetchone()[0]
        )

    def list_users(self) -> list[TeamMember]:
        """Return all members, admins first, then by email."""
        rows = self.conn.execute(
            "SELECT email, is_admin, is_consultant, added_by, created_at FROM users "
            "ORDER BY is_admin DESC, email;"
        ).fetchall()
        return [
            TeamMember(
                email=r["email"],
                roles=sorted(role.value for role in _roles(r)),
                added_by=r["added_by"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def put_user(self, email: str, roles: frozenset[Role], added_by: str) -> None:
        """Create or update a member with exactly ``roles`` (at least one)."""
        now = datetime.now(UTC).isoformat()
        with self.conn:
            self.conn.execute(
                "INSERT INTO users "
                "(email, is_admin, is_consultant, added_by, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(email) DO UPDATE SET "
                "is_admin = excluded.is_admin, is_consultant = excluded.is_consultant, "
                "updated_at = excluded.updated_at;",
                (
                    email,
                    int(Role.ADMIN in roles),
                    int(Role.SOLUTION_CONSULTANT in roles),
                    added_by,
                    now,
                    now,
                ),
            )

    def delete_user(self, email: str) -> bool:
        """Remove a member; return False when there was none."""
        with self.conn:
            cur = self.conn.execute("DELETE FROM users WHERE email = ?;", (email,))
        return cur.rowcount > 0
