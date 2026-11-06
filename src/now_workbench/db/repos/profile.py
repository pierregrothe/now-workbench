# src/now_workbench/db/repos/profile.py
# Repository mixin for the local profile, its pending email code and SMTP settings.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Profile repository mixin (ADR-012 sealed secrets for the SMTP password)."""

import sqlite3

from now_workbench.profile.models import MailSettings, MailSettingsUpdate, ProfileRecord

__all__ = ["SMTP_PASSWORD_SECRET", "ProfileRepositoryMixin"]

SMTP_PASSWORD_SECRET = "smtp_password"
_PROFILE_COLUMNS = (
    "display_name, email, avatar_kind, avatar_preset, avatar_updated_at, email_verified_at, "
    "code_hash, code_salt, code_expires_at, code_attempts, code_sent_at"
)


class ProfileRepositoryMixin:
    """Mixin for the singleton profile and mail-settings rows."""

    conn: sqlite3.Connection

    def get_secret(self, name: str) -> str:  # provided by PreferencesRepositoryMixin
        """Return a decrypted named secret."""
        raise NotImplementedError

    def set_secret(self, name: str, value: str) -> None:  # provided by PreferencesRepositoryMixin
        """Seal and store a named secret."""
        raise NotImplementedError

    def _ensure_profile_row(self) -> None:
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO profile (id) VALUES (1);")

    def get_profile(self) -> ProfileRecord:
        """Return the profile, creating the empty singleton row on first use."""
        self._ensure_profile_row()
        row = self.conn.execute(f"SELECT {_PROFILE_COLUMNS} FROM profile WHERE id = 1;").fetchone()
        return ProfileRecord(**dict(row))

    def update_profile_identity(self, display_name: str, email: str, now: str) -> ProfileRecord:
        """Set name and email; a changed email drops its verification and any pending code."""
        current = self.get_profile()
        with self.conn:
            if email != current.email:
                self.conn.execute(
                    "UPDATE profile SET email_verified_at = NULL, code_hash = NULL, "
                    "code_salt = NULL, code_expires_at = NULL, code_attempts = 0, "
                    "code_sent_at = NULL WHERE id = 1;"
                )
            self.conn.execute(
                "UPDATE profile SET display_name = ?, email = ?, updated_at = ? WHERE id = 1;",
                (display_name, email, now),
            )
        return self.get_profile()

    def set_profile_avatar(self, kind: str, preset: str | None, now: str) -> ProfileRecord:
        """Record which avatar is shown (none, a preset, or the uploaded picture)."""
        self._ensure_profile_row()
        with self.conn:
            self.conn.execute(
                "UPDATE profile SET avatar_kind = ?, avatar_preset = ?, avatar_updated_at = ?, "
                "updated_at = ? WHERE id = 1;",
                (kind, preset, now, now),
            )
        return self.get_profile()

    def store_verification_code(
        self, code_hash: str, salt: str, expires_at: str, sent_at: str
    ) -> None:
        """Save a freshly sent code (hash only) and reset the attempt counter."""
        self._ensure_profile_row()
        with self.conn:
            self.conn.execute(
                "UPDATE profile SET code_hash = ?, code_salt = ?, code_expires_at = ?, "
                "code_attempts = 0, code_sent_at = ? WHERE id = 1;",
                (code_hash, salt, expires_at, sent_at),
            )

    def record_failed_attempt(self) -> int:
        """Count one wrong code and return the new attempt total."""
        self._ensure_profile_row()
        with self.conn:
            self.conn.execute("UPDATE profile SET code_attempts = code_attempts + 1 WHERE id = 1;")
        return int(
            self.conn.execute("SELECT code_attempts FROM profile WHERE id = 1;").fetchone()[0]
        )

    def clear_verification_code(self) -> None:
        """Discard the pending code."""
        self._ensure_profile_row()
        with self.conn:
            self.conn.execute(
                "UPDATE profile SET code_hash = NULL, code_salt = NULL, code_expires_at = NULL, "
                "code_attempts = 0 WHERE id = 1;"
            )

    def mark_email_verified(self, now: str) -> ProfileRecord:
        """Approve the profile's email and clear the pending code."""
        self._ensure_profile_row()
        with self.conn:
            self.conn.execute(
                "UPDATE profile SET email_verified_at = ?, code_hash = NULL, code_salt = NULL, "
                "code_expires_at = NULL, code_attempts = 0, updated_at = ? WHERE id = 1;",
                (now, now),
            )
        return self.get_profile()

    def get_mail_settings(self) -> MailSettings:
        """Return the SMTP settings (defaults when never saved)."""
        row = self.conn.execute(
            "SELECT host, port, username, from_address, starttls FROM mail_settings WHERE id = 1;"
        ).fetchone()
        if row is None:
            return MailSettings()
        return MailSettings(
            host=row["host"],
            port=row["port"],
            username=row["username"],
            from_address=row["from_address"],
            starttls=bool(row["starttls"]),
        )

    def put_mail_settings(self, update: MailSettingsUpdate) -> MailSettings:
        """Save SMTP settings; the password is sealed and only changed when provided."""
        with self.conn:
            self.conn.execute(
                "INSERT INTO mail_settings (id, host, port, username, from_address, starttls) "
                "VALUES (1, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET host = excluded.host, "
                "port = excluded.port, username = excluded.username, "
                "from_address = excluded.from_address, starttls = excluded.starttls;",
                (
                    update.host,
                    update.port,
                    update.username,
                    update.from_address,
                    int(update.starttls),
                ),
            )
        if update.password is not None:
            self.set_secret(SMTP_PASSWORD_SECRET, update.password)
        return self.get_mail_settings()
