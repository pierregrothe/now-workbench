# src/now_workbench/domains/conversations/__init__.py
# Public root of the conversations domain: other packages import only what is listed here.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Conversations domain (ADR-015)."""

from now_workbench.domains.conversations.attachment_repository import ChatRepository
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
    MAX_THREAD_CONTEXT_MESSAGES,
    Attachment,
    ChatMessageCreate,
    ChatMessageRecord,
    ChatThreadCreate,
    ChatThreadRecord,
    ChatThreadUpdate,
    ConversationLimits,
)
from now_workbench.domains.conversations.repository import ThreadRepository

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
    "delete_files",
    "get_limits",
    "LimitReachedError",
    "MAX_THREAD_CONTEXT_MESSAGES",
    "read_bytes",
    "set_limits",
    "store_attachment",
    "ThreadRepository",
    "UnsupportedFileError",
]
