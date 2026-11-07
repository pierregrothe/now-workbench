# src/now_workbench/interfaces/ai/tools/navigate.py
# Otto moves the interface: open a screen, a Settings section, or a pre-filled action.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Navigation tool (ADR-026).

The command travels with Otto's reply and the chat applies it when the reply arrives, so Otto
can take the person to the right place ("this is where you approve shares") or open the
Actions screen with an action filled in, for them to review and run themselves.
"""

from typing import Any

from now_workbench.domains.identity import is_admin
from now_workbench.interfaces.ai.tools.base import (
    REGISTRY,
    ToolContext,
    ToolResult,
    ToolSpec,
    register,
)

__all__ = ["SCREENS", "SETTINGS_SECTIONS"]

SCREENS: dict[str, str] = {
    "home": "Home: the conversation with Otto and the overview",
    "artifacts": "Artifact library: demo bundles (clone, deploy, share, export, delete)",
    "synthesizer": "Use-Case Synthesizer: generate a demo bundle from a description",
    "capture": "Media Capture: screenshots and videos of an instance",
    "fluent": "Fluent SDK Explorer: a bundle's tables and schema diffs",
    "admin": "Workbench Settings (pick a section)",
    "actions": "Actions: every capability as a form (pick an action to pre-fill it)",
    "welcome": "Welcome guide",
}
SETTINGS_SECTIONS = (
    "profile",
    "team",
    "groups",
    "approvals",
    "impersonate",
    "claude",
    "limits",
    "capture",
    "synthesis",
    "workspace",
    "instances",
)


def _open_screen(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    screen = str(args["screen"])
    if screen not in SCREENS:
        return ToolResult(summary=f"Unknown screen '{screen}'.", ok=False)
    cmd: dict[str, Any] = {"type": "navigate", "tab": screen}
    where = SCREENS[screen].split(":")[0]
    section = args.get("section")
    if section:
        if screen != "admin" or section not in SETTINGS_SECTIONS:
            return ToolResult(summary=f"'{section}' is not a Settings section.", ok=False)
        cmd["section"] = section
        where = f"Settings > {section}"
    action = args.get("action")
    if action:
        spec = REGISTRY.get(str(action))
        if screen != "actions" or spec is None or spec.category == "visual":
            return ToolResult(summary=f"'{action}' is not an action to open.", ok=False)
        if spec.admin_only and not is_admin(ctx.actor()):
            return ToolResult(summary=f"'{action}' is for administrators.", ok=False)
        cmd["action"] = spec.name
        cmd["args"] = dict(args.get("args") or {})
        where = f"Actions > {spec.name}"
    return ToolResult(summary=f"Opened {where} for the person.", ui=[cmd])


register(
    ToolSpec(
        name="open_screen",
        description=(
            "Move the person's interface. Use it to show where something lives, to take them "
            "to a screen they asked for, or to open the Actions screen with an action and its "
            "arguments pre-filled so they can review and run it themselves. Screens: "
            + "; ".join(f"{k} ({v})" for k, v in SCREENS.items())
            + f". Settings sections (screen 'admin'): {', '.join(SETTINGS_SECTIONS)}."
        ),
        properties={
            "screen": {"type": "string", "enum": list(SCREENS)},
            "section": {"type": "string", "enum": list(SETTINGS_SECTIONS)},
            "action": {"type": "string", "description": "Tool name to pre-fill (screen 'actions')"},
            "args": {"type": "object", "description": "Arguments to pre-fill for the action"},
        },
        required=["screen"],
        handler=_open_screen,
        category="navigation",
    )
)
