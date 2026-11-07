# src/now_workbench/interfaces/api/errors.py
# How refusals read over HTTP: unsafe identifiers and domain errors become status codes.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Exception handlers shared by every route (ADR-025)."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from now_workbench.platform.config.paths import UnsafePathError
from now_workbench.platform.errors import (
    ConflictError,
    DomainError,
    ForbiddenError,
    InvalidInputError,
    NotFoundError,
)

__all__ = ["install_error_handlers"]

_DOMAIN_STATUS: dict[type[DomainError], int] = {
    NotFoundError: 404,
    ForbiddenError: 403,
    ConflictError: 409,
    InvalidInputError: 422,
}


def install_error_handlers(app: FastAPI) -> None:
    """Register the handlers on ``app``; the message is meant for the person, never a trace."""

    @app.exception_handler(UnsafePathError)
    async def _reject_unsafe_path(_request: Request, exc: UnsafePathError) -> JSONResponse:
        """Turn a rejected user-supplied id into HTTP 400 on every route (never 500)."""
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(DomainError)
    async def _domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        """Map a service's refusal to its status code."""
        return JSONResponse(status_code=_DOMAIN_STATUS[type(exc)], content={"detail": str(exc)})
