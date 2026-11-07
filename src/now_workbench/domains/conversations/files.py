# src/now_workbench/domains/conversations/files.py
# Attachment storage, type detection, limit checks and Claude content blocks (ADR-021).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Attachments and conversation limits.

The file's own bytes decide its type (PDF, PNG, JPEG, GIF, WebP, or UTF-8 text); the name and
the type the browser claims are never trusted. Bytes live under ``<data>/attachments/<id>``
with a random id, so no user-supplied name reaches the file system.
"""

import base64
import uuid
from datetime import UTC, datetime
from pathlib import Path

from now_workbench.domains.conversations.models import (
    Attachment,
    ChatThreadRecord,
    ConversationLimits,
)
from now_workbench.domains.profile import sniff_image
from now_workbench.platform.config.settings import settings

__all__ = [
    "LimitReachedError",
    "UnsupportedFileError",
    "check_can_ask",
    "claude_blocks",
    "delete_files",
    "detect_media_type",
    "read_bytes",
    "store_attachment",
]

_MB = 1024 * 1024
_TEXT_SUFFIXES = frozenset(".txt .md .csv .json .log .xml .yaml .yml .ts .js .py .html".split())
_SAFE_NAME = 120


class LimitReachedError(ValueError):
    """A conversation or upload limit set by the administrators was reached."""


class UnsupportedFileError(ValueError):
    """The file is not a type Claude can read."""


def _directory() -> Path:
    path = settings.get_data_dir() / "attachments"
    path.mkdir(parents=True, exist_ok=True)
    return path


def detect_media_type(data: bytes, filename: str) -> str:
    """Return the media type from the bytes (text also needs a known text extension).

    Raises:
        UnsupportedFileError: Not a PDF, a supported image or UTF-8 text.
    """
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    image = sniff_image(data)
    if image:
        return image
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if Path(filename).suffix.lower() in _TEXT_SUFFIXES and b"\x00" not in data:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            return "text/plain"
    raise UnsupportedFileError("Attach a PDF, an image (PNG, JPEG, GIF, WebP) or a text file.")


def check_can_ask(thread: ChatThreadRecord, limits: ConversationLimits) -> None:
    """Refuse a new question once the conversation used its token budget or is too old.

    Raises:
        LimitReachedError: Token or age limit reached.
    """
    if thread.tokens_used >= limits.max_conversation_tokens:
        raise LimitReachedError(
            f"This conversation used its budget of {limits.max_conversation_tokens:,} tokens. "
            "Start a new conversation to continue."
        )
    age = datetime.now(UTC) - _aware(thread.created_at)
    if age.days >= limits.max_age_days:
        raise LimitReachedError(
            f"This conversation is older than {limits.max_age_days} days and is read-only. "
            "Start a new conversation to continue."
        )


def _aware(value: str) -> datetime:
    stamp = datetime.fromisoformat(value)
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)


def store_attachment(
    thread_id: str,
    filename: str,
    data: bytes,
    existing: list[Attachment],
    limits: ConversationLimits,
) -> Attachment:
    """Check the limits and the type, then write the bytes.

    Args:
        thread_id: Conversation the file belongs to.
        filename: Name to show (trimmed; never used as a path).
        data: The file's bytes.
        existing: Attachments already in the conversation.
        limits: Current limits.

    Returns:
        The attachment record to persist.

    Raises:
        LimitReachedError: Too large, too many, or the conversation total is exceeded.
        UnsupportedFileError: Not a type Claude reads.
    """
    if not data:
        raise UnsupportedFileError("The file is empty.")
    if len(data) > limits.max_file_mb * _MB:
        raise LimitReachedError(f"Files can be at most {limits.max_file_mb} MB.")
    if len(existing) >= limits.max_files:
        raise LimitReachedError(f"A conversation can hold at most {limits.max_files} files.")
    if sum(a.size_bytes for a in existing) + len(data) > limits.max_conversation_mb * _MB:
        raise LimitReachedError(
            f"Attachments in one conversation can total at most {limits.max_conversation_mb} MB."
        )
    media_type = detect_media_type(data, filename)
    att = Attachment(
        id=f"att-{uuid.uuid4().hex}",
        thread_id=thread_id,
        filename=(Path(filename).name.strip() or "file")[:_SAFE_NAME],
        media_type=media_type,
        size_bytes=len(data),
        created_at=datetime.now(UTC).isoformat(),
    )
    (_directory() / att.id).write_bytes(data)
    return att


def read_bytes(attachment: Attachment) -> bytes:
    """Return an attachment's bytes."""
    return (_directory() / attachment.id).read_bytes()


def delete_files(attachments: list[Attachment]) -> None:
    """Remove the bytes of these attachments."""
    for att in attachments:
        (_directory() / att.id).unlink(missing_ok=True)


def claude_blocks(attachments: list[Attachment]) -> list[dict[str, object]]:
    """Return Messages API content blocks for these files (placed before the question)."""
    blocks: list[dict[str, object]] = []
    for att in attachments:
        data = read_bytes(att)
        if att.media_type == "text/plain":
            blocks.append(
                {
                    "type": "document",
                    "title": att.filename,
                    "source": {
                        "type": "text",
                        "media_type": "text/plain",
                        "data": data.decode("utf-8"),
                    },
                }
            )
            continue
        encoded = base64.standard_b64encode(data).decode("ascii")
        kind = "document" if att.media_type == "application/pdf" else "image"
        block: dict[str, object] = {
            "type": kind,
            "source": {"type": "base64", "media_type": att.media_type, "data": encoded},
        }
        if kind == "document":
            block["title"] = att.filename
        blocks.append(block)
    return blocks
