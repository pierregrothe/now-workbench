# src/now_workbench/interfaces/api/allowance.py
# The monthly-allowance gate every Claude entry point passes before calling Claude (ADR-031).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Allowance gate.

Called by every route that sends a new question to Claude (thread messages, the Otto
WebSocket and its legacy stream). An architecture test fails the build if one of them stops
calling it.
"""

import sqlite3

from now_workbench.domains.conversations import ChatRepository
from now_workbench.domains.identity import current_actor
from now_workbench.domains.telemetry import check_allowance
from now_workbench.platform.clock import utc_now

__all__ = ["enforce_allowance", "AllowanceExhaustedError"]


class AllowanceExhaustedError(RuntimeError):
    """The person used their monthly Claude allowance; no Claude call may be made."""


def enforce_allowance(conn: sqlite3.Connection) -> str:
    """Refuse when the acting person's allowance is used up; else return any warning.

    Args:
        conn: Open connection (owner scope is the acting person's).

    Returns:
        The 80% warning to show, or "" (also for administrators, who are exempt).

    Raises:
        AllowanceExhaustedError: 100% or more of the allowance is used.
        NoActorError: Nobody is signed in for this request (fail closed).
    """
    limits = ChatRepository(conn).get_conversation_limits()
    standing = check_allowance(conn, current_actor(), limits.monthly_allowance_tokens, utc_now())
    if standing.state == "refused":
        raise AllowanceExhaustedError(standing.message())
    return standing.message()
