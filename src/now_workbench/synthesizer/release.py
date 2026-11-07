# src/now_workbench/synthesizer/release.py
# Resolve the ServiceNow release a synthesized bundle targets (never typed by the user).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Release resolution for synthesis.

The release is read from the target instance's detected profile (ADR-014). With no
instance, or a release the platform has not reported yet, there is nothing to build for and
``NoReleaseError`` explains how to fix it; a release is never guessed.
"""

import sqlite3

from now_workbench.db import UNKNOWN_RELEASE
from now_workbench.db.repos.instances import InstanceRepository

__all__ = ["NoReleaseError", "resolve_synthesis_release"]


class NoReleaseError(RuntimeError):
    """No instance reports a release to build the bundle for."""


def resolve_synthesis_release(
    conn: sqlite3.Connection, explicit: str | None, instance_id: str | None
) -> str:
    """Return the release to build for: explicit value, else the target instance's.

    Args:
        conn: Open database connection.
        explicit: Release passed by the caller (CLI flag, chat tool), if any.
        instance_id: Target instance; None means the default instance.

    Returns:
        The release family name.

    Raises:
        LookupError: ``instance_id`` names an instance that does not exist.
        NoReleaseError: No explicit release, and the target instance (or the default
            instance) is missing or has not reported a release.
    """
    instance_repo = InstanceRepository(conn)
    if explicit:
        return explicit
    inst = (
        instance_repo.get_instance(instance_id)
        if instance_id
        else instance_repo.get_default_instance()
    )
    if instance_id and inst is None:
        raise LookupError(f"Instance '{instance_id}' not found")
    if inst is not None:
        profile = instance_repo.get_instance_profile(inst.id)
        if profile is not None and profile.release and profile.release != UNKNOWN_RELEASE:
            return profile.release
    raise NoReleaseError(
        "No release to build for: register an instance and test its connection so its "
        "release is detected."
    )
