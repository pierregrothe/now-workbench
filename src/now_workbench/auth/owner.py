# src/now_workbench/auth/owner.py
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
from typing import TYPE_CHECKING

from now_workbench.auth.models import LOCAL_EMAIL

if TYPE_CHECKING:
    from now_workbench.db.repository import DatabaseRepository

__all__ = ["NoOwnerError", "current_owner", "operator_owner", "owner_scope"]

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


def operator_owner(repo: DatabaseRepository, local_mode: bool) -> str:
    """Return who server start-up and the CLI act as, claiming orphaned rows for them.

    The earliest administrator; in local mode (no Cloudflare Access) the local operator when
    there is none; otherwise "" (rows wait for the first administrator to be set up).

    Args:
        repo: Open repository.
        local_mode: True when Cloudflare Access is not configured.

    Returns:
        The owner email ("" before the first administrator exists behind Access).
    """
    owner = repo.first_admin_email() or (LOCAL_EMAIL if local_mode else "")
    if owner:
        repo.claim_orphans(owner)
    return owner
