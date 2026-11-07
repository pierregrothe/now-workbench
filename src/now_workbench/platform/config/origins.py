# src/now_workbench/platform/config/origins.py
# Browser Origin matching shared by the CORS middleware and WebSocket handlers.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Origin allow-list matching.

CORS only governs fetch/XHR; a WebSocket handshake ignores it, so WebSocket endpoints
must check the ``Origin`` header themselves with the same pattern.
"""

import re

__all__ = ["is_origin_allowed"]


def is_origin_allowed(origin: str | None, pattern: str) -> bool:
    """Return True when a request's Origin header is acceptable.

    Browsers always send ``Origin`` on cross-site requests and WebSocket handshakes,
    so a present value must match ``pattern``. A missing header means a non-browser
    client (CLI, test client, curl), which is not a cross-site attack vector.

    Args:
        origin: Value of the ``Origin`` header, or None when absent.
        pattern: Regular expression the whole origin must match.

    Returns:
        True if the origin is absent or matches.
    """
    if not origin:
        return True
    return re.fullmatch(pattern, origin) is not None
