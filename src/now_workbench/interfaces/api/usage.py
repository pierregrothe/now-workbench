# src/now_workbench/interfaces/api/usage.py
# Claude usage allowances over HTTP: your own standing, and the team view for administrators.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Usage API (ADR-031)."""

import sqlite3
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from now_workbench.domains import telemetry
from now_workbench.domains.conversations import ChatRepository
from now_workbench.domains.identity import AuthUser, Role
from now_workbench.domains.telemetry import Allowance, PersonAllowance
from now_workbench.interfaces.api.guard import current_user, require_role
from now_workbench.platform.clock import utc_now
from now_workbench.platform.db.session import db_session

__all__ = ["router", "AllowanceOverride", "AllowanceView", "PersonAllowanceView"]

router = APIRouter(prefix="/api/usage", tags=["usage"])
# Refuse non-administrators before reading the body; the service checks again (ADR-025).
_admin = Depends(require_role(Role.ADMIN))
_anyone = Depends(current_user)


class AllowanceView(BaseModel):
    """A person's monthly standing, as the screens show it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    state: str
    used: int
    allowance: int
    percent: int
    resets_on: date

    @classmethod
    def of(cls, a: Allowance) -> AllowanceView:
        """Build the view of a standing."""
        return cls(
            state=a.state,
            used=a.used,
            allowance=a.allowance,
            percent=a.percent,
            resets_on=a.resets_on,
        )


class PersonAllowanceView(AllowanceView):
    """One team member's standing (administrators)."""

    email: str
    overridden: bool

    @classmethod
    def of_person(cls, p: PersonAllowance) -> PersonAllowanceView:
        """Build the view of a team member's standing."""
        return cls(**AllowanceView.of(p).model_dump(), email=p.email, overridden=p.overridden)


class AllowanceOverride(BaseModel):
    """A person's monthly allowance; null returns them to the default."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    monthly_tokens: int | None


def _default(conn: sqlite3.Connection) -> int:
    return ChatRepository(conn).get_conversation_limits().monthly_allowance_tokens


@router.get("/allowance", response_model=AllowanceView)
def my_allowance(user: AuthUser = _anyone) -> AllowanceView:
    """Your use and allowance this month (everyone; administrators are exempt)."""
    with db_session() as conn:
        return AllowanceView.of(telemetry.check_allowance(conn, user, _default(conn), utc_now()))


@router.get("/allowances", response_model=list[PersonAllowanceView])
def team_allowances(user: AuthUser = _admin) -> list[PersonAllowanceView]:
    """Everyone's use and allowance this month (administrators)."""
    with db_session() as conn:
        rows = telemetry.team_allowances(conn, user, _default(conn), utc_now())
    return [PersonAllowanceView.of_person(r) for r in rows]


@router.put("/allowances/{email}", response_model=list[PersonAllowanceView])
def set_allowance(
    email: str, req: AllowanceOverride, user: AuthUser = _admin
) -> list[PersonAllowanceView]:
    """Set a person's allowance, or return them to the default (administrators)."""
    with db_session() as conn:
        telemetry.set_allowance_override(conn, user, email, req.monthly_tokens)
    return team_allowances(user)
