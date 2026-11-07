# src/now_workbench/domains/identity/owner.py
# Who server start-up and the CLI act as; claims rows created before the first admin.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Operator identity for start-up and the CLI (ADR-018)."""

import sqlite3

from now_workbench.domains.identity.repository import UserRepository
from now_workbench.platform.owner import LOCAL_EMAIL

__all__ = ["operator_owner"]


def operator_owner(conn: sqlite3.Connection, local_mode: bool) -> str:
    """Return who server start-up and the CLI act as, claiming orphaned rows for them.

    The earliest administrator; in local mode (no Cloudflare Access) the local operator when
    there is none; otherwise "" (rows wait for the first administrator to be set up).

    Args:
        conn: Open database connection.
        local_mode: True when Cloudflare Access is not configured.

    Returns:
        The owner email ("" before the first administrator exists behind Access).
    """
    user_repo = UserRepository(conn)
    owner = user_repo.first_admin_email() or (LOCAL_EMAIL if local_mode else "")
    if owner:
        user_repo.claim_orphans(owner)
    return owner
