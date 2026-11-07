# src/now_workbench/platform/errors.py
# Errors a domain service raises; each front door (API, Otto's tools) maps them its own way.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Domain errors (ADR-025).

Services never speak HTTP. The API turns these into status codes in one exception handler;
Otto's tools turn them into a failed tool result carrying the same message.
"""

__all__ = ["ConflictError", "DomainError", "ForbiddenError", "InvalidInputError", "NotFoundError"]


class DomainError(Exception):
    """A request the domain refuses; the message is safe to show to the person."""


class NotFoundError(DomainError):
    """The record does not exist, or the person may not know it exists."""


class ForbiddenError(DomainError):
    """The person may see the record but not do this to it."""


class ConflictError(DomainError):
    """The request clashes with the current state (duplicate, last administrator, ...)."""


class InvalidInputError(DomainError):
    """The request is well formed but its values are not acceptable."""
