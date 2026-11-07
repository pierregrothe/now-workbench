# src/now_workbench/db/repos/users.py
# Repository mixin for the people allowed into the workbench and their roles.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Users repository mixin (ADR-017)."""

import sqlite3
from datetime import UTC, datetime

from now_workbench.auth.models import Role, TeamMember
from now_workbench.db.repos.base import Repository

__all__ = ["UserRepository"]


def _roles(row: sqlite3.Row) -> frozenset[Role]:
    roles: set[Role] = set()
    if row["is_admin"]:
        roles.add(Role.ADMIN)
    if row["is_consultant"]:
        roles.add(Role.SOLUTION_CONSULTANT)
    return frozenset(roles)


class UserRepository(Repository):
    """Repository for the ``users`` table."""

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

    def first_admin_email(self) -> str:
        """Return the earliest administrator's email, or "" when there is none."""
        row = self.conn.execute(
            "SELECT email FROM users WHERE is_admin = 1 ORDER BY created_at, email LIMIT 1;"
        ).fetchone()
        return str(row["email"]) if row else ""

    def claim_orphans(self, email: str) -> None:
        """Give rows created before any administrator existed (owner "") to ``email``."""
        with self.conn:
            for table in ("instances", "chat_threads", "seed_operations", "artifacts"):
                self.conn.execute(
                    f"UPDATE {table} SET owner_email = ? WHERE owner_email = '';", (email,)
                )
            self.conn.execute(
                "UPDATE user_preferences SET email = ? WHERE email = '' "
                "AND NOT EXISTS (SELECT 1 FROM user_preferences WHERE email = ?);",
                (email, email),
            )
            self.conn.execute("DELETE FROM user_preferences WHERE email = '';")

    def get_impersonation(self, real_email: str) -> str | None:
        """Return who ``real_email`` is acting as, or None."""
        row = self.conn.execute(
            "SELECT target_email FROM impersonations WHERE real_email = ?;", (real_email,)
        ).fetchone()
        return str(row["target_email"]) if row else None

    def start_impersonation(self, real_email: str, target_email: str) -> None:
        """Make ``real_email`` act as ``target_email`` (replacing any earlier one), logged."""
        with self.conn:
            self.conn.execute(
                "INSERT INTO impersonations (real_email, target_email) VALUES (?, ?) "
                "ON CONFLICT(real_email) DO UPDATE SET target_email = excluded.target_email, "
                "started_at = excluded.started_at;",
                (real_email, target_email),
            )
            self.conn.execute(
                "INSERT INTO impersonation_log (real_email, target_email, action) "
                "VALUES (?, ?, 'start');",
                (real_email, target_email),
            )

    def end_impersonation(self, real_email: str, action: str = "stop") -> bool:
        """Stop acting as someone else; ``action`` is 'stop' or 'revoked' in the log."""
        target = self.get_impersonation(real_email)
        if target is None:
            return False
        with self.conn:
            self.conn.execute("DELETE FROM impersonations WHERE real_email = ?;", (real_email,))
            self.conn.execute(
                "INSERT INTO impersonation_log (real_email, target_email, action) "
                "VALUES (?, ?, ?);",
                (real_email, target, action),
            )
        return True

    def delete_user(self, email: str) -> bool:
        """Remove a member; return False when there was none."""
        with self.conn:
            cur = self.conn.execute("DELETE FROM users WHERE email = ?;", (email,))
        return cur.rowcount > 0
