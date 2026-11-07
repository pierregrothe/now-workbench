# src/now_workbench/interfaces/api/feedback.py
# Ratings of Otto's replies over HTTP: rate or re-rate a reply, and list the ratings.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Reply feedback API (PRD-002). Feedback stays in the workbench database, never sent out."""

from fastapi import APIRouter, Depends

from now_workbench.domains.conversations import (
    FeedbackCreate,
    MessageFeedback,
    list_feedback,
    rate_reply,
)
from now_workbench.domains.identity import AuthUser
from now_workbench.interfaces.api.guard import current_user
from now_workbench.platform.db.session import db_session

__all__ = ["list_reply_feedback", "put_reply_feedback", "router"]

router = APIRouter(prefix="/api/feedback", tags=["feedback"])
_anyone = Depends(current_user)


@router.get("", response_model=list[MessageFeedback])
def list_reply_feedback(user: AuthUser = _anyone) -> list[MessageFeedback]:
    """Ratings with the reply text: everyone's for administrators, otherwise your own."""
    with db_session() as conn:
        return list_feedback(conn, user)


@router.put("/{message_id}", response_model=MessageFeedback)
def put_reply_feedback(message_id: str, req: FeedbackCreate) -> MessageFeedback:
    """Rate one of Otto's replies in your conversations; rating again replaces it."""
    with db_session() as conn:
        return rate_reply(conn, message_id, req)
