"""Settings and diagnostics tools for the Otto agent (mirrors `workbench config ...`/`doctor`)."""

from typing import Any

from now_workbench.domains.instances import InstanceRepository
from now_workbench.domains.settings import PreferencesRepository, WorkbenchPreferencesUpdate
from now_workbench.interfaces.ai.tools.base import (
    ToolContext,
    ToolResult,
    ToolSpec,
    register,
    table_tile,
    text_tile,
)
from now_workbench.platform.config.settings import settings
from now_workbench.platform.sdk.runner import NowSdkRunner

_SECRET_FIELDS = {"anthropic_api_key"}
_SETTING_TYPES = {
    "str": {"type": "string"},
    "int": {"type": "integer"},
    "bool": {"type": "boolean"},
}


def _setting_properties() -> dict[str, Any]:
    props: dict[str, Any] = {}
    for name, field in WorkbenchPreferencesUpdate.model_fields.items():
        if name in _SECRET_FIELDS:
            continue
        ann = str(field.annotation)
        key = "bool" if "bool" in ann else "int" if "int" in ann else "str"
        props[name] = dict(_SETTING_TYPES[key])
    return props


def _show_settings(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    prefs = PreferencesRepository(ctx.conn).get_workbench_preferences().model_dump()
    prefs.pop("anthropic_api_key_masked", None)
    rows = [[k, v] for k, v in prefs.items() if k != "updated_at"]
    tile = table_tile("tile-settings", "Workbench settings", ["Setting", "Value"], rows)
    return ToolResult(
        summary=f"{len(rows)} settings loaded.",
        data={"settings": prefs},
        tiles=[tile],
    )


def _update_settings(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    changes = {k: v for k, v in args.items() if k in _setting_properties() and v is not None}
    if not changes:
        return ToolResult(summary="No valid settings were provided.", ok=False)
    PreferencesRepository(ctx.conn).update_workbench_preferences(
        WorkbenchPreferencesUpdate(**changes)
    )
    rows = [[k, v] for k, v in changes.items()]
    return ToolResult(
        summary="Updated settings: " + ", ".join(f"{k}={v}" for k, v in changes.items()) + ".",
        data={"changed": changes},
        tiles=[table_tile("tile-settings-updated", "Settings updated", ["Setting", "Value"], rows)],
    )


def _plan_reset_settings(ctx: ToolContext, args: dict[str, Any]) -> str:
    return "Reset all Workbench settings to factory defaults (capture, synthesis, ...)."


def _reset_settings(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    PreferencesRepository(ctx.conn).reset_workbench_preferences()
    return ToolResult(
        summary="Workbench settings were reset to factory defaults.",
        tiles=[text_tile("tile-settings-reset", "Settings reset", "Factory defaults restored.")],
    )


def _doctor(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    env = NowSdkRunner(
        now_sdk_bin=settings.now_sdk_bin, node_bin=settings.node_bin
    ).probe_environment()
    rows: list[list[Any]] = [[k, v] for k, v in env.items()]
    rows.append(["instances", len(InstanceRepository(ctx.conn).list_instances())])
    rows.append(
        [
            "otto_api_key",
            "configured"
            if PreferencesRepository(ctx.conn).get_decrypted_anthropic_api_key()
            else "missing",
        ]
    )
    return ToolResult(
        summary="Diagnostics complete.",
        data={"environment": {k: str(v) for k, v in env.items()}},
        tiles=[table_tile("tile-doctor", "Workbench diagnostics", ["Check", "Result"], rows)],
    )


register(
    ToolSpec(
        name="show_settings",
        description="Show current Workbench settings.",
        properties={},
        handler=_show_settings,
        category="config",
        cli_equivalent="config show",
    )
)
register(
    ToolSpec(
        name="update_settings",
        description="Change Workbench settings (model, capture, synthesis, welcome, ...).",
        properties=_setting_properties(),
        handler=_update_settings,
        category="config",
        cli_equivalent="config set",
    )
)
register(
    ToolSpec(
        name="reset_settings",
        description="Reset Workbench settings to factory defaults.",
        properties={},
        handler=_reset_settings,
        category="config",
        cli_equivalent="config reset",
        destructive=True,
        plan=_plan_reset_settings,
    )
)
register(
    ToolSpec(
        name="run_diagnostics",
        description="Run toolchain and environment diagnostics.",
        properties={},
        handler=_doctor,
        category="diagnostics",
        cli_equivalent="doctor",
    )
)
