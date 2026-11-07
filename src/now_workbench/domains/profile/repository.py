# src/now_workbench/domains/profile/repository.py
# Repository mixin for per-user profiles.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Profile repository."""

from now_workbench.domains.profile.models import ProfileRecord
from now_workbench.platform.db.repository import Repository

__all__ = ["ProfileRepository"]

_COLUMNS = "email, display_name, avatar_kind, avatar_preset, avatar_updated_at"


class ProfileRepository(Repository):
    """Repository for the ``profile`` table (one row per verified email)."""

    def get_profile(self, email: str) -> ProfileRecord:
        """Return the user's profile, creating an empty one on first use."""
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO profile (email) VALUES (?);", (email,))
        row = self.conn.execute(
            f"SELECT {_COLUMNS} FROM profile WHERE email = ?;", (email,)
        ).fetchone()
        return ProfileRecord(**dict(row))

    def update_profile_name(self, email: str, display_name: str, now: str) -> ProfileRecord:
        """Set the display name."""
        self.get_profile(email)
        with self.conn:
            self.conn.execute(
                "UPDATE profile SET display_name = ?, updated_at = ? WHERE email = ?;",
                (display_name, now, email),
            )
        return self.get_profile(email)

    def set_profile_avatar(
        self, email: str, kind: str, preset: str | None, now: str
    ) -> ProfileRecord:
        """Record which avatar is shown (none, a preset, or the uploaded picture)."""
        self.get_profile(email)
        with self.conn:
            self.conn.execute(
                "UPDATE profile SET avatar_kind = ?, avatar_preset = ?, avatar_updated_at = ?, "
                "updated_at = ? WHERE email = ?;",
                (kind, preset, now, now, email),
            )
        return self.get_profile(email)
