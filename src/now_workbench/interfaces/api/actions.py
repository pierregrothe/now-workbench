# src/now_workbench/interfaces/api/actions.py
# The action catalog: every capability Otto has, runnable by hand from the Actions screen.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Actions API (ADR-026).

The tool registry is the catalog of what the workbench can do. Listing it and running an
action here uses the very same definitions and rules as Otto: the person acts as themselves,
administrator actions are offered to administrators only, and changes that remove or decide
need a second, confirmed call.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from now_workbench.domains.identity import AuthUser, is_admin
from now_workbench.domains.settings import PreferencesRepository
from now_workbench.interfaces.ai.tools import REGISTRY
from now_workbench.interfaces.ai.tools.base import ToolContext, ToolSpec, execute_tool
from now_workbench.interfaces.api.guard import current_user
from now_workbench.platform.db.session import db_session

__all__ = ["router"]

router = APIRouter(prefix="/api/actions", tags=["actions"])

# Tools that only make sense inside a conversation with Otto.
_OTTO_ONLY = frozenset({"visual", "navigation", "confirmation"})


class ActionInfo(BaseModel):
    """One action as the Actions screen shows it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    description: str
    category: str
    destructive: bool
    properties: dict[str, Any]
    required: list[str]


class ActionRun(BaseModel):
    """Arguments of one run; `confirmed` is the second call of a change that needs it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    args: dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False


def _offered(spec: ToolSpec, user: AuthUser) -> bool:
    return spec.category not in _OTTO_ONLY and (is_admin(user) or not spec.admin_only)


@router.get("", response_model=list[ActionInfo])
def list_actions(user: AuthUser = Depends(current_user)) -> list[ActionInfo]:
    """The actions the signed-in person may run, grouped by category then name."""
    specs = sorted(
        (s for s in REGISTRY.values() if _offered(s, user)), key=lambda s: (s.category, s.name)
    )
    return [
        ActionInfo(
            name=s.name,
            description=s.description,
            category=s.category,
            destructive=s.destructive,
            properties=s.properties,
            required=list(s.required),
        )
        for s in specs
    ]


@router.post("/{name}")
def run_action(name: str, req: ActionRun, user: AuthUser = Depends(current_user)) -> dict[str, Any]:
    """Run an action as the signed-in person; the result carries tiles to display."""
    spec = REGISTRY.get(name)
    if spec is None or not _offered(spec, user):
        raise HTTPException(status_code=404, detail="No such action.")
    with db_session() as conn:
        fake = PreferencesRepository(conn).get_workbench_preferences().sdk_fake_mode
        result = execute_tool(
            ToolContext(conn=conn, fake_mode=fake, user=user), name, req.args, req.confirmed
        )
    return result.model_dump(include={"ok", "summary", "pending", "tiles", "layout"})
