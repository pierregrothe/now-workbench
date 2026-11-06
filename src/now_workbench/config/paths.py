# src/now_workbench/config/paths.py
# Safe resolution of user-supplied identifiers into direct children of a trusted root.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Path containment for bundle, template and other user-supplied identifiers.

A bundle id from an HTTP request, a manifest inside an imported archive, or an AI
tool argument becomes a directory name that is later copied, extracted or removed
recursively. ``safe_child`` is the single gate every such use must go through, so
a value such as ``..`` or ``../../home`` can never address anything outside the
root directory.
"""

import re
from pathlib import Path

__all__ = ["UnsafePathError", "safe_child"]

# Starts alphanumeric, then letters, digits, dot, underscore, hyphen. No separators.
_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


class UnsafePathError(ValueError):
    """Raised when a name cannot be used as a direct child of a root directory."""


def safe_child(root: Path, name: str) -> Path:
    """Return ``root / name`` after proving it is a direct child of ``root``.

    Args:
        root: Trusted directory (it need not exist yet).
        name: Untrusted identifier, e.g. a bundle id.

    Returns:
        The resolved child path.

    Raises:
        UnsafePathError: The name is empty, too long, contains a path separator or
            ``..``, or resolves (e.g. through a symlink) outside ``root``.
    """
    if not isinstance(name, str) or not _NAME_PATTERN.fullmatch(name) or ".." in name:
        raise UnsafePathError(
            f"Invalid name {name!r}: use letters, digits, '.', '_' or '-' (max 128 characters)."
        )
    base = root.resolve()
    candidate = (base / name).resolve()
    if candidate.parent != base:
        raise UnsafePathError(f"Name {name!r} resolves outside {base}.")
    return candidate
