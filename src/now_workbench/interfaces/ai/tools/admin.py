# src/now_workbench/interfaces/ai/tools/admin.py
# Otto's administration tools: the team, conversation limits and usage allowances (admins).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Administration tools (ADR-017, ADR-021, ADR-025, ADR-031).

The services refuse anyone who is not an administrator, so these tools are inert for
everyone else. Impersonation has no tool by the owner's decision: it stays a UI action.
"""

from typing import Any

from now_workbench.domains import conversations, identity, telemetry
from now_workbench.domains.conversations import ConversationLimits
from now_workbench.domains.identity import TeamMember
from now_workbench.domains.telemetry import PersonAllowance
from now_workbench.interfaces.ai.tools.base import (
    ToolContext,
    ToolResult,
    ToolSpec,
    register,
    table_tile,
)
from now_workbench.platform.clock import utc_now

__all__: list[str] = []

_EMAIL = {"type": "string", "description": "Email address"}
_LIMIT_FIELDS = list(ConversationLimits.model_fields)


def _team_tile(team: list[TeamMember]) -> Any:
    rows = [[m.email, ", ".join(m.roles), m.added_by] for m in team]
    return table_tile("tile-team", "Team", ["Email", "Roles", "Added by"], rows)


def _list_team(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    team = identity.list_team(ctx.conn, ctx.actor())
    return ToolResult(
        summary=f"{len(team)} people can use the workbench.",
        data={"team": [m.model_dump() for m in team]},
        tiles=[_team_tile(team)],
    )


def _set_roles(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    team = identity.set_roles(
        ctx.conn,
        ctx.actor(),
        str(args["email"]),
        bool(args.get("admin")),
        bool(args.get("solution_consultant")),
    )
    return ToolResult(summary=f"Updated {args['email']}.", tiles=[_team_tile(team)])


def _remove_member(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    team = identity.remove_member(ctx.conn, ctx.actor(), str(args["email"]))
    return ToolResult(summary=f"Removed {args['email']}'s access.", tiles=[_team_tile(team)])


def _limits_tile(limits: ConversationLimits) -> Any:
    rows = [[k, v] for k, v in limits.model_dump().items()]
    return table_tile("tile-limits", "Conversation limits", ["Limit", "Value"], rows)


def _show_limits(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    limits = conversations.get_limits(ctx.conn)
    return ToolResult(
        summary="Conversation limits loaded.",
        data=limits.model_dump(),
        tiles=[_limits_tile(limits)],
    )


def _set_limits(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    current = conversations.get_limits(ctx.conn).model_dump()
    changes = {k: v for k, v in args.items() if k in _LIMIT_FIELDS and v is not None}
    limits = conversations.set_limits(
        ctx.conn, ctx.actor(), ConversationLimits.model_validate({**current, **changes})
    )
    return ToolResult(
        summary="Limits saved; they apply to everyone now.",
        data=limits.model_dump(),
        tiles=[_limits_tile(limits)],
    )


def _allowances_tile(rows: list[PersonAllowance]) -> Any:
    table = [
        [
            r.email,
            f"{r.used:,}",
            "exempt" if r.state == "exempt" else f"{r.allowance:,}",
            "-" if r.state == "exempt" else f"{r.percent}%",
            "override" if r.overridden else "default",
        ]
        for r in rows
    ]
    return table_tile(
        "tile-allowances",
        "Claude usage this month",
        ["Email", "Used", "Allowance", "Used %", "Set by"],
        table,
    )


def _team_allowances(ctx: ToolContext) -> list[PersonAllowance]:
    default = conversations.get_limits(ctx.conn).monthly_allowance_tokens
    return telemetry.team_allowances(ctx.conn, ctx.actor(), default, utc_now())


def _usage_allowances(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    rows = _team_allowances(ctx)
    return ToolResult(
        summary=f"Claude usage this month for {len(rows)} people (billable tokens).",
        data={"people": [r.model_dump(mode="json") | {"percent": r.percent} for r in rows]},
        tiles=[_allowances_tile(rows)],
    )


def _set_usage_allowance(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    tokens = args.get("monthly_tokens")
    telemetry.set_allowance_override(
        ctx.conn, ctx.actor(), str(args["email"]), None if tokens is None else int(tokens)
    )
    what = "the default" if tokens is None else f"{int(tokens):,} tokens a month"
    return ToolResult(
        summary=f"{args['email']} now has {what}.",
        tiles=[_allowances_tile(_team_allowances(ctx))],
    )


register(
    ToolSpec(
        name="list_team",
        description="List who may use the workbench and their roles (administrators).",
        properties={},
        handler=_list_team,
        admin_only=True,
        category="admin",
    )
)
register(
    ToolSpec(
        name="set_team_roles",
        description=(
            "Add a person or change their roles (administrators). Give at least one role; "
            "the last administrator cannot lose the admin role."
        ),
        properties={
            "email": _EMAIL,
            "admin": {"type": "boolean"},
            "solution_consultant": {"type": "boolean"},
        },
        required=["email"],
        handler=_set_roles,
        admin_only=True,
        category="admin",
        destructive=True,
        plan=lambda ctx, a: (
            f"Give {a.get('email')} the roles: "
            + ", ".join(r for r in ("admin", "solution_consultant") if a.get(r))
            + "."
        ),
    )
)
register(
    ToolSpec(
        name="remove_team_member",
        description="Remove a person's access to the workbench (administrators).",
        properties={"email": _EMAIL},
        required=["email"],
        handler=_remove_member,
        admin_only=True,
        category="admin",
        destructive=True,
        plan=lambda ctx, a: f"Remove {a.get('email')}'s access to the workbench.",
    )
)
register(
    ToolSpec(
        name="show_limits",
        description="Show the conversation limits (tokens, age, attachments) for everyone.",
        properties={},
        handler=_show_limits,
        category="admin",
    )
)
register(
    ToolSpec(
        name="set_limits",
        description="Change conversation limits for everyone (administrators); omit unchanged.",
        properties={k: {"type": "integer"} for k in _LIMIT_FIELDS},
        handler=_set_limits,
        admin_only=True,
        category="admin",
        destructive=True,
        plan=lambda ctx, a: (
            "Set limits: " + ", ".join(f"{k}={v}" for k, v in a.items() if k in _LIMIT_FIELDS) + "."
        ),
    )
)
register(
    ToolSpec(
        name="usage_allowances",
        description=(
            "Show everyone's billable Claude tokens this month against their monthly "
            "allowance (administrators; administrators themselves are exempt)."
        ),
        properties={},
        handler=_usage_allowances,
        admin_only=True,
        category="admin",
    )
)
register(
    ToolSpec(
        name="set_usage_allowance",
        description=(
            "Set one person's monthly Claude allowance in billable tokens (100,000 to "
            "1,000,000,000), or null to return them to the default (administrators)."
        ),
        properties={
            "email": _EMAIL,
            "monthly_tokens": {"type": ["integer", "null"], "description": "Tokens a month"},
        },
        required=["email", "monthly_tokens"],
        handler=_set_usage_allowance,
        admin_only=True,
        category="admin",
        destructive=True,
        plan=lambda ctx, a: (
            f"Set {a.get('email')}'s monthly allowance to "
            + ("the default" if a.get("monthly_tokens") is None else f"{a['monthly_tokens']:,}")
            + "."
        ),
    )
)
