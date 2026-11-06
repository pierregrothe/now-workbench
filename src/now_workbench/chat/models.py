# src/now_workbench/chat/models.py
# Conversation limits set by administrators and the attachment record (ADR-021).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Chat models."""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["Attachment", "ConversationLimits"]


class ConversationLimits(BaseModel):
    """One global set of limits, edited by administrators, applied to everyone.

    Attributes:
        max_turns: Questions a person may ask in one conversation.
        max_age_days: Days after it starts that a conversation accepts new questions.
        max_file_mb: Largest single attachment.
        max_conversation_mb: Total attachments in one conversation.
        max_files: Attachments in one conversation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_turns: int = Field(default=20, ge=1, le=500)
    max_age_days: int = Field(default=30, ge=1, le=3650)
    max_file_mb: int = Field(default=10, ge=1, le=32)
    max_conversation_mb: int = Field(default=25, ge=1, le=100)
    max_files: int = Field(default=10, ge=1, le=50)


class Attachment(BaseModel):
    """A file attached to a conversation (the bytes live on disk, never in the database)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    thread_id: str
    filename: str
    media_type: str
    size_bytes: int
    message_id: str | None = None
    created_at: str
