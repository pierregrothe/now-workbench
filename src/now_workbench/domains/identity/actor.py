# src/now_workbench/domains/identity/actor.py
# The person acting in the current request (email and roles), for rules beyond ownership.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Ambient actor (ADR-025).

The access middleware sets it next to the owner scope (ADR-018), so Otto's tools apply the
same rules as the API for the same person. Reading it outside a request fails closed.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from now_workbench.domains.identity.models import AuthUser

__all__ = ["NoActorError", "actor_scope", "current_actor"]

_ACTOR: ContextVar[AuthUser | None] = ContextVar("workbench_actor", default=None)


class NoActorError(RuntimeError):
    """A rule needed the signed-in person, but nobody is signed in for this work."""


def current_actor() -> AuthUser:
    """Return the person acting now.

    Raises:
        NoActorError: No actor scope is active.
    """
    actor = _ACTOR.get()
    if actor is None:
        raise NoActorError("No signed-in person for this action.")
    return actor


@contextmanager
def actor_scope(user: AuthUser) -> Iterator[AuthUser]:
    """Run a block as ``user``; nested scopes restore the outer actor on exit."""
    token = _ACTOR.set(user)
    try:
        yield user
    finally:
        _ACTOR.reset(token)
