# src/now_workbench/domains/conversations/__init__.py
# Public root of the conversations domain: other packages import only what is listed here.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Conversations domain (ADR-015)."""

from now_workbench.domains.conversations.attachment_repository import ChatRepository
from now_workbench.domains.conversations.feedback import list_feedback, rate_reply
from now_workbench.domains.conversations.feedback_repository import FeedbackRepository
from now_workbench.domains.conversations.files import (
    LimitReachedError,
    UnsupportedFileError,
    check_can_ask,
    claude_blocks,
    delete_files,
    read_bytes,
    store_attachment,
)
from now_workbench.domains.conversations.limits import get_limits, set_limits
from now_workbench.domains.conversations.models import (
    MAX_FEEDBACK_LISTED,
    MAX_THREAD_CONTEXT_MESSAGES,
    Attachment,
    ChatMessageCreate,
    ChatMessageRecord,
    ChatThreadCreate,
    ChatThreadRecord,
    ChatThreadUpdate,
    ConversationLimits,
    FeedbackCreate,
    MessageFeedback,
    ReplyRating,
)
from now_workbench.domains.conversations.repository import ThreadRepository
from now_workbench.domains.conversations.service import (
    delete_conversation,
    remove_attachment,
    update_conversation,
)

__all__ = [
    "Attachment",
    "ChatMessageCreate",
    "ChatMessageRecord",
    "ChatRepository",
    "ChatThreadCreate",
    "ChatThreadRecord",
    "ChatThreadUpdate",
    "check_can_ask",
    "claude_blocks",
    "ConversationLimits",
    "delete_conversation",
    "delete_files",
    "FeedbackCreate",
    "FeedbackRepository",
    "get_limits",
    "LimitReachedError",
    "list_feedback",
    "MAX_FEEDBACK_LISTED",
    "MAX_THREAD_CONTEXT_MESSAGES",
    "MessageFeedback",
    "rate_reply",
    "read_bytes",
    "remove_attachment",
    "ReplyRating",
    "set_limits",
    "store_attachment",
    "ThreadRepository",
    "UnsupportedFileError",
    "update_conversation",
]
