# src/now_workbench/domains/profile/service.py
# Changing one's own profile: display name and built-in avatar (shared by the API and Otto).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Profile service (ADR-025, ADR-026)."""

import sqlite3
from datetime import UTC, datetime

from now_workbench.domains.profile.avatars import PRESET_AVATARS, delete_avatar
from now_workbench.domains.profile.models import ProfileRecord, ProfileUpdate
from now_workbench.domains.profile.repository import ProfileRepository
from now_workbench.platform.errors import InvalidInputError

__all__ = ["choose_preset_avatar", "rename"]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def rename(conn: sqlite3.Connection, email: str, display_name: str) -> ProfileRecord:
    """Set the display name (validated like the profile form)."""
    name = ProfileUpdate(display_name=display_name).display_name
    return ProfileRepository(conn).update_profile_name(email, name, _now())


def choose_preset_avatar(conn: sqlite3.Connection, email: str, preset: str) -> ProfileRecord:
    """Use one of the built-in avatars instead of an uploaded picture.

    Raises:
        InvalidInputError: No built-in avatar has that name.
    """
    if preset not in PRESET_AVATARS:
        raise InvalidInputError(f"Unknown avatar. Built-in avatars: {', '.join(PRESET_AVATARS)}.")
    delete_avatar(email)
    return ProfileRepository(conn).set_profile_avatar(email, "preset", preset, _now())
