# src/now_workbench/platform/owner.py
# The signed-in owner of the current request, read by every owner-scoped repository query.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Ambient owner context (ADR-018).

The access middleware sets the verified email for the lifetime of each request or WebSocket.
Owner-scoped queries call :func:`current_owner`; when nothing set it they raise instead of
returning everyone's rows, so a forgotten scope fails closed.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

__all__ = ["LOCAL_EMAIL", "NoOwnerError", "current_owner", "owner_scope"]

# The operator when Cloudflare Access is not configured (local development).
LOCAL_EMAIL = "local@localhost"

_OWNER: ContextVar[str | None] = ContextVar("workbench_owner", default=None)


class NoOwnerError(RuntimeError):
    """An owner-scoped query ran outside any owner scope."""


def current_owner() -> str:
    """Return the email that owns the current request.

    Returns:
        The owner email ("" is the bucket for rows created before the first administrator).

    Raises:
        NoOwnerError: No owner scope is active.
    """
    owner = _OWNER.get()
    if owner is None:
        raise NoOwnerError("No signed-in owner for this operation.")
    return owner


@contextmanager
def owner_scope(email: str) -> Iterator[str]:
    """Run a block as ``email``; nested scopes restore the outer owner on exit.

    Args:
        email: The owner to act as.

    Yields:
        The email, for convenience.
    """
    token = _OWNER.set(email)
    try:
        yield email
    finally:
        _OWNER.reset(token)
