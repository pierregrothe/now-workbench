"""Instance registry tools for the Otto agent (mirrors `workbench instance ...`)."""

from typing import Any

from now_workbench.ai.tiles import GenerativeUIResponse, build_instance_response
from now_workbench.ai.tools.base import (
    ToolContext,
    ToolResult,
    ToolSpec,
    register,
    resolve_instance,
)
from now_workbench.connectivity import verify_instance_authentication
from now_workbench.db import InstanceCreate, InstanceRecord, InstanceUpdate


def _dicts(instances: list[InstanceRecord]) -> list[dict[str, Any]]:
    return [
        {
            "id": i.id,
            "name": i.name,
            "url": i.url,
            "release": i.release,
            "status": i.status,
            "is_default": i.is_default,
        }
        for i in instances
    ]


def _view(ctx: ToolContext, summary: str, detailed: bool = False) -> ToolResult:
    """Return the current registry as summary KPI or detailed cards."""
    instances = ctx.repo.list_instances()
    resp: GenerativeUIResponse = build_instance_response(
        _dicts(instances), detail_level="detailed" if detailed else "summary"
    )
    return ToolResult(
        summary=summary,
        data={"instances": _dicts(instances)},
        tiles=list(resp.tiles),
        layout=resp.layout,
    )


def _list_instances(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    count = len(ctx.repo.list_instances())
    return _view(ctx, f"{count} instance(s) registered.", bool(args.get("detailed")))


def _add_instance(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    url = str(args["url"]).strip().rstrip("/")
    existing = ctx.repo.list_instances()
    created = ctx.repo.add_instance(
        InstanceCreate(
            name=str(args.get("name") or url.split("://")[-1].split(".")[0]),
            url=url,
            username=str(args.get("username") or "admin"),
            password=str(args.get("password") or ""),
            release=str(args.get("release") or "Zurich"),
            is_default=bool(args.get("make_default")) or not existing,
        )
    )
    status, msg, _ = verify_instance_authentication(created, timeout=3.0, fake_mode=ctx.fake_mode)
    ctx.repo.update_instance_status(created.id, status)
    return _view(ctx, f"Registered '{created.name}' ({url}); authentication: {status} - {msg}.")


def _rename_instance(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    inst = resolve_instance(ctx.repo, args.get("instance"))
    new_name = str(args["new_name"]).strip()
    ctx.repo.update_instance(inst.id, InstanceUpdate(name=new_name))
    return _view(ctx, f"Renamed '{inst.name}' to '{new_name}'.", detailed=True)


def _update_instance(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    inst = resolve_instance(ctx.repo, args.get("instance"))
    fields = {
        k: args[k] for k in ("url", "username", "password", "release") if args.get(k) is not None
    }
    if not fields:
        return ToolResult(summary="No fields to update were provided.", ok=False)
    rec = ctx.repo.update_instance(inst.id, InstanceUpdate(**fields))
    if rec:
        status, _, _ = verify_instance_authentication(rec, timeout=3.0, fake_mode=ctx.fake_mode)
        ctx.repo.update_instance_status(rec.id, status)
    changed = ", ".join(k for k in fields if k != "password") or "credentials"
    return _view(ctx, f"Updated {changed} on '{inst.name}'.", detailed=True)


def _set_default(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    inst = resolve_instance(ctx.repo, args.get("instance"))
    ctx.repo.set_default_instance(inst.id)
    return _view(ctx, f"'{inst.name}' is now the default target.")


def _test_instances(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    refs = args.get("instances") or []
    targets = [resolve_instance(ctx.repo, r) for r in refs] if refs else ctx.repo.list_instances()
    lines: list[str] = []
    ok = 0
    for inst in targets:
        status, msg, _ = verify_instance_authentication(inst, timeout=3.5, fake_mode=ctx.fake_mode)
        ctx.repo.update_instance_status(inst.id, status)
        ok += 1 if status == "authenticated" else 0
        lines.append(f"{inst.name}: {status} ({msg})")
    detailed = len(targets) <= 4
    res = _view(ctx, f"Tested {len(targets)} instance(s): {ok} authenticated.", detailed)
    return ToolResult(
        summary=res.summary + " " + "; ".join(lines[:10]),
        data={"results": lines},
        tiles=res.tiles,
        layout=res.layout,
    )


def _select_for_delete(ctx: ToolContext, args: dict[str, Any]) -> list[InstanceRecord]:
    instances = ctx.repo.list_instances()
    mode = args.get("filter")
    if mode == "unauthenticated":
        return [i for i in instances if i.status != "authenticated"]
    if mode == "all_except_default":
        return [i for i in instances if not i.is_default]
    return [resolve_instance(ctx.repo, r) for r in (args.get("instances") or [])]


def _plan_delete(ctx: ToolContext, args: dict[str, Any]) -> str:
    targets = _select_for_delete(ctx, args)
    if not targets:
        return "No matching instances to delete."
    names = ", ".join(t.name for t in targets[:8]) + ("..." if len(targets) > 8 else "")
    return f"Delete {len(targets)} instance(s) from the registry: {names}"


def _delete_instances(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    targets = _select_for_delete(ctx, args)
    if not targets:
        return _view(ctx, "No matching instances were found; nothing deleted.")
    deleted = [t.name for t in targets if ctx.repo.delete_instance(t.id)]
    remaining = ctx.repo.list_instances()
    if remaining and not any(r.is_default for r in remaining):
        ctx.repo.set_default_instance(remaining[0].id)
    preview = ", ".join(deleted[:5]) + ("..." if len(deleted) > 5 else "")
    return _view(ctx, f"Deleted {len(deleted)} instance(s) ({preview}).")


_REF = {"type": "string", "description": "Instance id, name, or part of its URL"}

register(
    ToolSpec(
        name="list_instances",
        description=(
            "Show registered ServiceNow instances (summary by default, detailed cards on request)."
        ),
        properties={"detailed": {"type": "boolean"}},
        handler=_list_instances,
        category="instance",
        cli_equivalent="instance list",
    )
)
register(
    ToolSpec(
        name="add_instance",
        description="Register a new ServiceNow instance and verify its authentication.",
        properties={
            "url": {"type": "string"},
            "name": {"type": "string"},
            "username": {"type": "string"},
            "password": {"type": "string"},
            "release": {"type": "string"},
            "make_default": {"type": "boolean"},
        },
        required=["url"],
        handler=_add_instance,
        category="instance",
        cli_equivalent="instance add",
    )
)
register(
    ToolSpec(
        name="rename_instance",
        description="Rename a registered instance.",
        properties={"instance": _REF, "new_name": {"type": "string"}},
        required=["instance", "new_name"],
        handler=_rename_instance,
        category="instance",
        cli_equivalent="instance rename",
    )
)
register(
    ToolSpec(
        name="update_instance",
        description="Change an instance's URL, username, password, or release.",
        properties={
            "instance": _REF,
            "url": {"type": "string"},
            "username": {"type": "string"},
            "password": {"type": "string"},
            "release": {"type": "string"},
        },
        required=["instance"],
        handler=_update_instance,
        category="instance",
        cli_equivalent="instance add (edit)",
    )
)
register(
    ToolSpec(
        name="set_default_instance",
        description="Make an instance the active default target.",
        properties={"instance": _REF},
        required=["instance"],
        handler=_set_default,
        category="instance",
        cli_equivalent="instance activate",
    )
)
register(
    ToolSpec(
        name="test_instances",
        description="Test live authentication for named instances, or all when none are named.",
        properties={"instances": {"type": "array", "items": {"type": "string"}}},
        handler=_test_instances,
        category="instance",
        cli_equivalent="instance test",
    )
)
register(
    ToolSpec(
        name="delete_instances",
        description=(
            "Delete instances by reference, or by filter: 'unauthenticated' (every instance "
            "that is not authenticated) or 'all_except_default'."
        ),
        properties={
            "instances": {"type": "array", "items": {"type": "string"}},
            "filter": {"type": "string", "enum": ["unauthenticated", "all_except_default"]},
        },
        handler=_delete_instances,
        category="instance",
        cli_equivalent="instance delete",
        destructive=True,
        plan=_plan_delete,
    )
)
