# src/now_workbench/domains/conversations/models.py
# Threads, messages, conversation limits and attachments (ADR-021, ADR-023).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Conversation models."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "Attachment",
    "ChatMessageCreate",
    "ChatMessageRecord",
    "ChatThreadCreate",
    "ChatThreadRecord",
    "ChatThreadUpdate",
    "ConversationLimits",
    "MAX_THREAD_CONTEXT_MESSAGES",
]


class ConversationLimits(BaseModel):
    """One global set of limits, edited by administrators, applied to everyone.

    Attributes:
        max_conversation_tokens: Tokens one conversation may use with Claude, counted the
            way they are billed (cached input at a tenth). Then a new conversation is needed.
        compact_at_tokens: Input size at which Claude summarizes the earlier conversation
            (server-side compaction) so it keeps going in a smaller context.
        max_age_days: Days after it starts that a conversation accepts new questions.
        max_file_mb: Largest single attachment.
        max_conversation_mb: Total attachments in one conversation.
        max_files: Attachments in one conversation.
        monthly_allowance_tokens: Billable Claude tokens each non-administrator may use per
            UTC month across all conversations (ADR-031).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_conversation_tokens: int = Field(default=2_000_000, ge=50_000, le=50_000_000)
    compact_at_tokens: int = Field(default=150_000, ge=50_000, le=900_000)
    max_age_days: int = Field(default=30, ge=1, le=3650)
    max_file_mb: int = Field(default=10, ge=1, le=32)
    max_conversation_mb: int = Field(default=25, ge=1, le=100)
    max_files: int = Field(default=10, ge=1, le=50)
    monthly_allowance_tokens: int = Field(default=10_000_000, ge=100_000, le=1_000_000_000)


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


MAX_THREAD_CONTEXT_MESSAGES = 20


class ChatThreadRecord(BaseModel):
    """Conversational thread metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    archived: bool = False
    target_tab: str = "home"
    # Tokens used with Claude against the admin-set budget (ADR-023).
    tokens_used: int = 0
    max_tokens: int = 2_000_000
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ChatThreadCreate(BaseModel):
    """Payload to create a new conversational thread."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str | None = None
    title: str = "Workspace Orchestration Session"
    target_tab: str = "home"


class ChatThreadUpdate(BaseModel):
    """Payload to update or archive/unarchive a conversational thread."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str | None = None
    archived: bool | None = None
    target_tab: str | None = None


class ChatMessageCreate(BaseModel):
    """Payload to append a message to a conversational thread."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str
    role: str = "user"
    widget_type: str | None = None
    widget_data: dict[str, Any] | None = None
    attachment_ids: list[str] = Field(default_factory=list, max_length=50)


class ChatMessageRecord(BaseModel):
    """Chat message in a conversational thread."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    thread_id: str
    role: str
    content: str
    widget_type: str | None = None
    widget_data: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
