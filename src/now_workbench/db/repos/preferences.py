"""Preferences and sealed-secret repository mixin (ADR-012)."""

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from now_workbench.auth.owner import current_owner
from now_workbench.config.crypto import mask_api_key, seal_secret, unseal_secret
from now_workbench.db.models import (
    WorkbenchPreferences,
    WorkbenchPreferencesUpdate,
)

__all__ = ["PreferencesRepositoryMixin"]

ANTHROPIC_KEY_SECRET = "anthropic_api_key"
_DERIVED_FIELDS = (
    "anthropic_api_key_masked",
    "has_anthropic_api_key",
    "anthropic_api_key_from_env",
)


def _env_api_key() -> str:
    """Return the Claude key from the server environment (``WORKBENCH_ANTHROPIC_API_KEY``)."""
    from now_workbench.config.settings import settings

    return settings.anthropic_api_key.strip()


def _secret_context(name: str) -> str:
    """Return the GCM binding label for a named application secret."""
    return f"secret:{name}"


class PreferencesRepositoryMixin:
    """Mixin providing per-user preferences and shared named sealed secrets."""

    conn: sqlite3.Connection

    def get_secret(self, name: str) -> str:
        """Return a decrypted named secret, or an empty string when unset."""
        row = self.conn.execute("SELECT sealed FROM secrets WHERE name = ?;", (name,)).fetchone()
        return unseal_secret(row["sealed"], _secret_context(name)) if row else ""

    def set_secret(self, name: str, value: str) -> None:
        """Seal and store a named secret; an empty value deletes it."""
        with self.conn:
            if not value:
                self.conn.execute("DELETE FROM secrets WHERE name = ?;", (name,))
                return
            self.conn.execute(
                """
                INSERT INTO secrets (name, sealed, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    sealed = excluded.sealed, updated_at = excluded.updated_at;
                """,
                (name, seal_secret(value, _secret_context(name)), datetime.now(UTC).isoformat()),
            )

    def _load_preferences_payload(self) -> dict[str, Any]:
        """Load the owner's preferences payload, initializing defaults on first use."""
        row = self.conn.execute(
            "SELECT payload FROM user_preferences WHERE email = ?;", (current_owner(),)
        ).fetchone()
        if row:
            return dict(json.loads(row["payload"]))

        from now_workbench.config.settings import settings

        payload = WorkbenchPreferences(claude_model=settings.claude_model).model_dump(
            exclude=set(_DERIVED_FIELDS)
        )
        self._write_preferences_payload(payload)
        return payload

    def _write_preferences_payload(self, payload: dict[str, Any]) -> None:
        """Persist the owner's preferences row."""
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO user_preferences (email, payload, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    payload = excluded.payload, updated_at = excluded.updated_at;
                """,
                (current_owner(), json.dumps(payload), payload["updated_at"]),
            )

    def get_decrypted_anthropic_api_key(self) -> str:
        """Return the Claude key: the server environment's when set, else the stored one."""
        return _env_api_key() or self.get_secret(ANTHROPIC_KEY_SECRET)

    def get_workbench_preferences(self) -> WorkbenchPreferences:
        """Fetch preferences with a masked API key preview (never the key itself)."""
        payload = self._load_preferences_payload()
        raw_key = self.get_decrypted_anthropic_api_key()
        return WorkbenchPreferences(
            **payload,
            anthropic_api_key_masked=mask_api_key(raw_key),
            has_anthropic_api_key=bool(raw_key),
            anthropic_api_key_from_env=bool(_env_api_key()),
        )

    def update_workbench_preferences(
        self, update: WorkbenchPreferencesUpdate
    ) -> WorkbenchPreferences:
        """Merge a partial update; a new API key is sealed into the secrets table.

        Raises:
            ValueError: A new key was supplied while one is already stored.
        """
        payload = self._load_preferences_payload()
        patch = update.model_dump(exclude_none=True)
        new_key = (
            str(patch.pop("anthropic_api_key", "")).strip()
            if "anthropic_api_key" in patch
            else None
        )
        # A masked preview echoed back by the UI is never a real key.
        if new_key is not None and "..." not in new_key:
            if _env_api_key():
                raise ValueError("The Claude API key is set in the server .env file.")
            if new_key and self.get_secret(ANTHROPIC_KEY_SECRET):
                msg = (
                    "An active API key exists. You must explicitly delete "
                    "the existing key before setting a new key."
                )
                raise ValueError(msg)
            self.set_secret(ANTHROPIC_KEY_SECRET, new_key)
        payload.update(patch)
        payload["updated_at"] = datetime.now(UTC).isoformat()
        self._write_preferences_payload(payload)
        return self.get_workbench_preferences()

    def delete_anthropic_api_key(self) -> WorkbenchPreferences:
        """Explicitly remove the stored Claude API key."""
        self.set_secret(ANTHROPIC_KEY_SECRET, "")
        return self.get_workbench_preferences()

    def reset_workbench_preferences(self) -> WorkbenchPreferences:
        """Reset the owner's preferences to defaults; the shared Claude key is untouched."""
        with self.conn:
            self.conn.execute("DELETE FROM user_preferences WHERE email = ?;", (current_owner(),))
        return self.get_workbench_preferences()
