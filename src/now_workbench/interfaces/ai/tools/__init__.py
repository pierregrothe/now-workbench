"""Otto agent tool registry: every CLI capability exposed as a typed, callable action."""

from typing import Any

from now_workbench.interfaces.ai.tools import (
    admin,
    bundles,
    captures,
    demos,
    instances,
    operations,
    sharing,
    show,
    system,
)
from now_workbench.interfaces.ai.tools.base import (
    REGISTRY,
    ToolContext,
    ToolResult,
    ToolSpec,
    text_tile,
)

__all__ = [
    "REGISTRY",
    "admin",
    "ToolContext",
    "ToolResult",
    "ToolSpec",
    "bundles",
    "captures",
    "demos",
    "execute_tool",
    "instances",
    "operations",
    "sharing",
    "show",
    "system",
    "tool_definitions",
]


def tool_definitions() -> list[dict[str, Any]]:
    """Return Anthropic tool definitions for the whole registry."""
    return [spec.definition() for spec in REGISTRY.values()]


def _confirmation_result(spec: ToolSpec, ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    plan = spec.plan(ctx, args) if spec.plan else f"Run {spec.name}."
    tile = text_tile(
        f"tile-confirm-{spec.name}",
        "Confirm action",
        plan,
        [
            {
                "id": "confirm_tool",
                "label": "Confirm",
                "variant": "primary",
                "tool": spec.name,
                "tool_input": args,
                "plan": plan,
            },
            {"id": "cancel_tool", "label": "Cancel", "variant": "secondary"},
        ],
    )
    return ToolResult(
        summary=f"Waiting for your confirmation: {plan}",
        pending=True,
        tiles=[tile],
    )


def execute_tool(
    ctx: ToolContext,
    name: str,
    args: dict[str, Any],
    confirmed: bool = False,
) -> ToolResult:
    """Execute a registered tool; destructive tools require prior confirmation."""
    spec = REGISTRY.get(name)
    if spec is None:
        return ToolResult(summary=f"Unknown tool '{name}'.", ok=False)
    if spec.destructive and not confirmed:
        try:
            return _confirmation_result(spec, ctx, args)
        except Exception as exc:
            return ToolResult(summary=f"Could not prepare '{name}': {exc}", ok=False)
    try:
        return spec.handler(ctx, args)
    except Exception as exc:
        return ToolResult(summary=f"{name} failed: {exc}", ok=False)
