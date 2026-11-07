# src/now_workbench/domains/conversations/limits.py
# The global conversation limits: everyone reads them, administrators change them.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Conversation limits service (ADR-021, ADR-023, ADR-025)."""

import sqlite3

from now_workbench.domains.conversations.attachment_repository import ChatRepository
from now_workbench.domains.conversations.models import ConversationLimits
from now_workbench.domains.identity import AuthUser, require_admin

__all__ = ["get_limits", "set_limits"]


def get_limits(conn: sqlite3.Connection) -> ConversationLimits:
    """The limits everyone works under."""
    return ChatRepository(conn).get_conversation_limits()


def set_limits(
    conn: sqlite3.Connection, actor: AuthUser, limits: ConversationLimits
) -> ConversationLimits:
    """Change the limits for everyone (administrators).

    Raises:
        ForbiddenError: The actor is not an administrator.
    """
    require_admin(actor)
    repo = ChatRepository(conn)
    repo.put_conversation_limits(limits, updated_by=actor.email)
    return repo.get_conversation_limits()
