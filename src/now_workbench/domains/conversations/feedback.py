# src/now_workbench/domains/conversations/feedback.py
# Rating Otto's replies and listing the ratings: your own, or everyone's for administrators.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Reply feedback service (PRD-002, ADR-025)."""

import sqlite3

from now_workbench.domains.conversations.feedback_repository import FeedbackRepository
from now_workbench.domains.conversations.models import FeedbackCreate, MessageFeedback
from now_workbench.domains.identity import AuthUser, is_admin
from now_workbench.platform.errors import InvalidInputError, NotFoundError

__all__ = ["list_feedback", "rate_reply"]


def rate_reply(conn: sqlite3.Connection, message_id: str, req: FeedbackCreate) -> MessageFeedback:
    """Rate one of Otto's replies in the owner's conversations; rating again replaces it.

    Raises:
        NotFoundError: The message does not exist or is in someone else's conversation.
        InvalidInputError: The message is not one of Otto's replies.
    """
    repo = FeedbackRepository(conn)
    role = repo.message_role(message_id)
    if role is None:
        raise NotFoundError("Message not found.")
    if role != "assistant":
        raise InvalidInputError("Only Otto's replies can be rated.")
    repo.put(message_id, req.rating, req.comment)
    stored = repo.get(message_id)
    assert stored is not None
    return stored


def list_feedback(conn: sqlite3.Connection, actor: AuthUser) -> list[MessageFeedback]:
    """Everyone's ratings for an administrator, otherwise the actor's own."""
    repo = FeedbackRepository(conn)
    return repo.list_all() if is_admin(actor) else repo.list_own()
