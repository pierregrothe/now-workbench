"""Otto agent tool registry: every CLI capability exposed as a typed, callable action."""

from typing import Any

from now_workbench.interfaces.ai.tools import (
    account,
    admin,
    bundles,
    captures,
    confirm,
    demos,
    history,
    instances,
    navigate,
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
    execute_tool,
)

__all__ = [
    "REGISTRY",
    "account",
    "admin",
    "ToolContext",
    "ToolResult",
    "ToolSpec",
    "bundles",
    "captures",
    "confirm",
    "demos",
    "execute_tool",
    "history",
    "instances",
    "navigate",
    "operations",
    "sharing",
    "show",
    "system",
    "tool_definitions",
]


def tool_definitions(admin: bool = True) -> list[dict[str, Any]]:
    """Return the Anthropic tool definitions a person may use (ADR-026).

    Args:
        admin: The person is a workbench administrator; otherwise admin-only tools are left out.
    """
    return [spec.definition() for spec in REGISTRY.values() if admin or not spec.admin_only]
