# src/now_workbench/interfaces/api/impersonation.py
# Start, inspect and stop acting as someone else (ADR-020).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Impersonation API. Every decision uses the person really signed in, never the target."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from now_workbench.domains.identity import AuthUser, UserRepository, candidates, may_impersonate
from now_workbench.interfaces.api.guard import current_user
from now_workbench.platform.db.session import db_session

__all__ = ["ImpersonationStatus", "router"]

router = APIRouter(prefix="/api/impersonation", tags=["impersonation"])
_log = logging.getLogger("uvicorn.error")


class ImpersonationStatus(BaseModel):
    """Who is signed in, who the requests act as, and who else they may act as."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    real_email: str
    acting_as: str | None
    candidates: list[str]


class StartRequest(BaseModel):
    """The person to act as."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    email: str


def _status(user: AuthUser) -> ImpersonationStatus:
    real = user.signed_in
    with db_session() as conn:
        return ImpersonationStatus(
            real_email=real.email,
            acting_as=user.email if user.real_email else None,
            candidates=candidates(conn, real),
        )


@router.get("", response_model=ImpersonationStatus)
def impersonation_status(user: AuthUser = Depends(current_user)) -> ImpersonationStatus:
    """Report the current impersonation and the people you may act as."""
    return _status(user)


@router.post("", response_model=ImpersonationStatus)
def start_impersonation(
    req: StartRequest, user: AuthUser = Depends(current_user)
) -> ImpersonationStatus:
    """Act as someone you are allowed to (administrators: anyone; group admins: members)."""
    real = user.signed_in
    target = req.email.strip().lower()
    with db_session() as conn:
        if not may_impersonate(conn, real, target):
            raise HTTPException(status_code=403, detail=f"You cannot act as {target}.")
        UserRepository(conn).start_impersonation(real.email, target)
    _log.warning("Impersonation started: %s is acting as %s.", real.email, target)
    acting = AuthUser(
        email=target,
        roles=frozenset(),
        mode=real.mode,
        real_email=real.email,
        real_roles=real.roles,
    )
    return _status(acting)


@router.delete("", response_model=ImpersonationStatus)
def stop_impersonation(user: AuthUser = Depends(current_user)) -> ImpersonationStatus:
    """Go back to being yourself."""
    real = user.signed_in
    with db_session() as conn:
        if UserRepository(conn).end_impersonation(real.email):
            _log.warning("Impersonation stopped: %s is themselves again.", real.email)
    return _status(real)
