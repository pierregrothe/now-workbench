"""Preferences and secret repository mixin."""

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from now_workbench.config.crypto import decrypt_secret, encrypt_secret, mask_api_key
from now_workbench.db.models import (
    WorkbenchPreferences,
    WorkbenchPreferencesUpdate,
)


class PreferencesRepositoryMixin:
    """Mixin providing preferences and AES-256 secret encryption storage."""

    conn: sqlite3.Connection

    def _load_raw_preferences_dict(self) -> dict[str, Any]:
        """Load raw stored preferences dictionary from SQLite or initialize encrypted default."""
        cursor = self.conn.execute(
            "SELECT payload FROM workbench_preferences WHERE id = 'default';"
        )
        row = cursor.fetchone()
        if row:
            return dict(json.loads(row["payload"]))

        from now_workbench.config.settings import settings

        raw_key = settings.anthropic_api_key.strip()
        encrypted_key = encrypt_secret(raw_key) if raw_key else ""
        default_prefs = WorkbenchPreferences(
            anthropic_api_key_masked=mask_api_key(raw_key),
            has_anthropic_api_key=bool(raw_key),
            claude_model=settings.claude_model,
        )
        stored = default_prefs.model_dump()
        stored.pop("anthropic_api_key_masked", None)
        stored.pop("has_anthropic_api_key", None)
        stored["anthropic_api_key_encrypted"] = encrypted_key

        with self.conn:
            self.conn.execute(
                """
                INSERT INTO workbench_preferences (id, payload, updated_at)
                VALUES ('default', ?, ?);
                """,
                (json.dumps(stored), default_prefs.updated_at),
            )
        return stored

    def get_decrypted_anthropic_api_key(self) -> str:
        """Decrypt and return the stored Claude AI API key for internal backend use."""
        stored = self._load_raw_preferences_dict()
        enc_val = str(stored.get("anthropic_api_key_encrypted", ""))
        return decrypt_secret(enc_val)

    def get_workbench_preferences(self) -> WorkbenchPreferences:
        """Fetch persisted Now Workbench preferences with masked API key preview."""
        stored = self._load_raw_preferences_dict()
        enc_val = str(stored.pop("anthropic_api_key_encrypted", ""))
        raw_key = decrypt_secret(enc_val)
        stored["anthropic_api_key_masked"] = mask_api_key(raw_key)
        stored["has_anthropic_api_key"] = bool(raw_key)
        return WorkbenchPreferences(**stored)

    def update_workbench_preferences(
        self, update: WorkbenchPreferencesUpdate
    ) -> WorkbenchPreferences:
        """Encrypt secrets and merge partial updates into persisted preferences."""
        stored = self._load_raw_preferences_dict()
        patch_data = update.model_dump(exclude_none=True)

        if "anthropic_api_key" in patch_data:
            new_raw_key = str(patch_data.pop("anthropic_api_key")).strip()
            # Ignore masked preview strings if accidentally echoed back
            if "..." not in new_raw_key:
                if new_raw_key:
                    existing_enc = str(stored.get("anthropic_api_key_encrypted", "")).strip()
                    if existing_enc:
                        msg = (
                            "An active API key exists. You must explicitly delete "
                            "the existing key before setting a new key."
                        )
                        raise ValueError(msg)
                    stored["anthropic_api_key_encrypted"] = encrypt_secret(new_raw_key)
                else:
                    stored["anthropic_api_key_encrypted"] = ""

        stored.update(patch_data)
        now_iso = datetime.now(UTC).isoformat()
        stored["updated_at"] = now_iso

        with self.conn:
            self.conn.execute(
                """
                INSERT INTO workbench_preferences (id, payload, updated_at)
                VALUES ('default', ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    payload=excluded.payload,
                    updated_at=excluded.updated_at;
                """,
                (json.dumps(stored), now_iso),
            )
        return self.get_workbench_preferences()

    def delete_anthropic_api_key(self) -> WorkbenchPreferences:
        """Explicitly remove and clear the stored Claude AI API key."""
        stored = self._load_raw_preferences_dict()
        stored["anthropic_api_key_encrypted"] = ""
        now_iso = datetime.now(UTC).isoformat()
        stored["updated_at"] = now_iso
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO workbench_preferences (id, payload, updated_at)
                VALUES ('default', ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    payload=excluded.payload,
                    updated_at=excluded.updated_at;
                """,
                (json.dumps(stored), now_iso),
            )
        return self.get_workbench_preferences()

    def reset_workbench_preferences(self) -> WorkbenchPreferences:
        """Reset Now Workbench preferences to factory defaults."""
        with self.conn:
            self.conn.execute("DELETE FROM workbench_preferences WHERE id = 'default';")
        return self.get_workbench_preferences()
