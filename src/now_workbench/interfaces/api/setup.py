# src/now_workbench/interfaces/api/setup.py
# First-run setup: the signed-in person enters the code from the server log to become admin.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Setup API (ADR-017)."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from now_workbench.domains.identity import (
    AuthUser,
    Role,
    SetupCodes,
    SetupError,
    TooManyAttemptsError,
    UserRepository,
    WrongCodeError,
)
from now_workbench.interfaces.api.guard import current_user
from now_workbench.platform.db.session import db_session

__all__ = ["SetupStatus", "router"]

router = APIRouter(prefix="/api/setup", tags=["setup"])


class SetupStatus(BaseModel):
    """What the UI needs to decide between the app, the setup dialog and a no-access page."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    setup_required: bool
    email: str
    has_role: bool
    auth_mode: str


class SetupRequest(BaseModel):
    """The code read from the server log."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=4, max_length=32)


def _codes(request: Request) -> SetupCodes:
    codes: SetupCodes = request.app.state.setup_codes
    return codes


@router.get("/status", response_model=SetupStatus)
def setup_status(user: AuthUser = Depends(current_user)) -> SetupStatus:
    """Report whether the first administrator still has to be created."""
    with db_session() as conn:
        required = user.mode == "cloudflare" and UserRepository(conn).count_admins() == 0
    return SetupStatus(
        setup_required=required,
        email=user.email,
        has_role=bool(user.roles),
        auth_mode=user.mode,
    )


@router.post("", response_model=SetupStatus)
def complete_setup(
    req: SetupRequest, request: Request, user: AuthUser = Depends(current_user)
) -> SetupStatus:
    """Make the signed-in person the first administrator when the setup code matches."""
    if user.mode != "cloudflare":
        raise HTTPException(status_code=409, detail="Local mode needs no setup.")
    with db_session() as conn:
        user_repo = UserRepository(conn)
        if user_repo.count_admins() > 0:
            raise HTTPException(status_code=409, detail="This workbench is already set up.")
        try:
            _codes(request).redeem(req.code)
        except WrongCodeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except TooManyAttemptsError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except SetupError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        user_repo.put_user(user.email, frozenset(Role), added_by="first-run setup")
        user_repo.claim_orphans(user.email)
    return SetupStatus(setup_required=False, email=user.email, has_role=True, auth_mode=user.mode)
