# src/now_workbench/profile/avatars.py
# Built-in avatar ids and safe storage of an uploaded profile picture.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Avatar presets and uploaded-picture storage (PNG, JPEG or WebP only; never SVG)."""

import hashlib
from pathlib import Path

from now_workbench.config.settings import settings

__all__ = [
    "MAX_AVATAR_BYTES",
    "PRESET_AVATARS",
    "delete_avatar",
    "load_avatar",
    "save_avatar",
    "sniff_image",
]

# Must match web/src/profile/avatars.ts (a test compares them).
PRESET_AVATARS: tuple[str, ...] = (
    "sun",
    "leaf",
    "wave",
    "peak",
    "moon",
    "spark",
    "cube",
    "bloom",
    "orbit",
    "fox",
    "owl",
    "robot",
)
MAX_AVATAR_BYTES = 2 * 1024 * 1024

_EXTENSIONS = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}


def sniff_image(data: bytes) -> str | None:
    """Return the content type from the file's own bytes, or None when unsupported.

    The client-declared type and file name are never trusted.
    """
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _directory() -> Path:
    path = settings.get_data_dir() / "avatars"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _stem(email: str) -> str:
    """File name stem for a user: a hash, so the email never reaches the file system."""
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()[:24]


def delete_avatar(email: str) -> None:
    """Remove the user's stored uploaded picture."""
    for ext in _EXTENSIONS.values():
        (_directory() / f"{_stem(email)}.{ext}").unlink(missing_ok=True)


def save_avatar(email: str, data: bytes, content_type: str) -> None:
    """Store the user's uploaded picture, replacing any previous one."""
    delete_avatar(email)
    (_directory() / f"{_stem(email)}.{_EXTENSIONS[content_type]}").write_bytes(data)


def load_avatar(email: str) -> tuple[bytes, str] | None:
    """Return the user's stored picture and its content type, or None."""
    for content_type, ext in _EXTENSIONS.items():
        path = _directory() / f"{_stem(email)}.{ext}"
        if path.is_file():
            return path.read_bytes(), content_type
    return None
