"""Demo lifecycle tools for the Otto agent (seed, rollback, properties, stage verification)."""

from typing import Any

from now_workbench.domains.instances import InstanceRepository, is_simulated
from now_workbench.domains.properties import PropertyEngine
from now_workbench.domains.runbooks import RunbookEngine
from now_workbench.domains.seed import SeedEngine, SeedRepository
from now_workbench.interfaces.ai.tools.base import (
    BUNDLE_ARG,
    ToolContext,
    ToolResult,
    ToolSpec,
    register,
    resolve_instance,
    run_async,
    table_tile,
    text_tile,
)
from now_workbench.interfaces.ai.tools.bundles import bundle_path

_INST = {"type": "string", "description": "Instance id/name; defaults to the default instance"}


def _operation_is_fake(ctx: ToolContext, operation_id: str) -> bool:
    """Simulate when the context says so or the operation's instance is simulated."""
    op = SeedRepository(ctx.conn).get_seed_operation(operation_id)
    target = InstanceRepository(ctx.conn).get_instance(op.instance_id) if op else None
    return is_simulated(target, ctx.fake_mode) if target else ctx.fake_mode


def _seed(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    inst = resolve_instance(ctx.conn, args.get("instance"))
    engine = SeedEngine(conn=ctx.conn, fake_mode=is_simulated(inst, ctx.fake_mode))
    path = bundle_path(ctx.conn, bundle_id)
    op = run_async(engine.load_and_seed(bundle_id, path, instance_id=inst.id))
    return ToolResult(
        summary=f"Seeded '{bundle_id}' to '{inst.name}': {len(op.created_records)} record(s) "
        f"(operation {op.id}).",
        data={"operation_id": op.id, "records": len(op.created_records)},
        tiles=[
            text_tile(
                f"tile-seed-{op.id}",
                "Seed complete",
                f"{len(op.created_records)} record(s) created on {inst.name}.\nOperation: {op.id}",
            )
        ],
    )


def _plan_rollback(ctx: ToolContext, args: dict[str, Any]) -> str:
    op = SeedRepository(ctx.conn).get_seed_operation(str(args["operation_id"]))
    if not op:
        return f"Seed operation '{args['operation_id']}' was not found."
    return (
        f"Delete {len(op.created_records)} record(s) created by seed operation "
        f"{op.id} (bundle {op.bundle_id})."
    )


def _rollback(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    op_id = str(args["operation_id"])
    engine = SeedEngine(conn=ctx.conn, fake_mode=_operation_is_fake(ctx, op_id))
    deleted, errors = run_async(engine.rollback(op_id))
    return ToolResult(
        summary=f"Rolled back {op_id}: {deleted} record(s) deleted, {len(errors)} error(s).",
        ok=not errors,
        data={"deleted": deleted, "errors": errors[:5]},
        tiles=[
            text_tile(f"tile-rb-{op_id}", "Rollback", f"{deleted} deleted; {len(errors)} errors.")
        ],
    )


def _seed_history(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    ops = SeedRepository(ctx.conn).list_seed_operations(limit=int(args.get("limit") or 10))
    rows = [
        [o.id, o.bundle_id, o.instance_id, o.status, len(o.created_records), o.error or "-"]
        for o in ops
    ]
    tile = table_tile(
        "tile-seed-history",
        "Seed history",
        ["Operation", "Bundle", "Instance", "Status", "Records", "Error"],
        rows,
    )
    return ToolResult(
        summary=f"{len(ops)} seed operation(s) on record.",
        data={"operations": [[*r[:4], r[5]] for r in rows]},
        tiles=[tile],
    )


def _verify_seed(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    op_id = str(args["operation_id"])
    fake = _operation_is_fake(ctx, op_id)
    checks = run_async(SeedEngine(conn=ctx.conn, fake_mode=fake).verify(op_id))
    present = sum(1 for _item, ok, _d in checks if ok)
    rows = [[i.table, i.sys_id, "present" if ok else "MISSING", d] for i, ok, d in checks]
    tile = table_tile(
        f"tile-verify-{op_id}", "Seeded records", ["Table", "sys_id", "State", "Detail"], rows
    )
    return ToolResult(
        summary=f"{present}/{len(checks)} record(s) of {op_id} exist on the instance.",
        ok=present == len(checks),
        data={"records": rows},
        tiles=[tile],
    )


def _plan_reset(ctx: ToolContext, args: dict[str, Any]) -> str:
    return (
        f"Reset demo '{args['bundle_id']}': roll back its seed records and restore the "
        "original system properties."
    )


def _reset(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    bundle_path(ctx.conn, bundle_id)
    inst = resolve_instance(ctx.conn, args.get("instance"))
    fake = is_simulated(inst, ctx.fake_mode)
    seed_engine = SeedEngine(conn=ctx.conn, fake_mode=fake)
    ops = [
        o
        for o in SeedRepository(ctx.conn).list_seed_operations(limit=100)
        if o.bundle_id == bundle_id and o.status != "rolled_back" and o.instance_id == inst.id
    ]
    rolled = 0
    for o in ops:
        count, _ = run_async(seed_engine.rollback(o.id))
        rolled += count
    prop = run_async(
        PropertyEngine().restore_properties(bundle_id=bundle_id, instance=inst, fake_mode=fake)
    )
    return ToolResult(
        summary=f"Reset '{bundle_id}' on '{inst.name}': {rolled} record(s) rolled back, "
        f"{prop.restored_count} propert(ies) restored.",
        data={"rolled_back": rolled, "restored": prop.restored_count},
        tiles=[
            text_tile(
                f"tile-reset-{bundle_id}",
                "Demo reset",
                f"{rolled} records rolled back; {prop.restored_count} properties restored.",
            )
        ],
    )


def _verify_stage(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    guide = RunbookEngine().load_runbook(bundle_path(ctx.conn, bundle_id), bundle_id=bundle_id)
    if not guide:
        return ToolResult(summary=f"'{bundle_id}' has no walkthrough guide.", ok=False)
    step = int(args["step_number"])
    stage = next((s for s in guide.stages if s.step_number == step), None)
    if not stage:
        return ToolResult(summary=f"Stage {step} not found in '{bundle_id}'.", ok=False)
    inst = resolve_instance(ctx.conn, args.get("instance"))
    ok, msg = run_async(
        RunbookEngine().verify_stage(stage, inst, fake_mode=is_simulated(inst, ctx.fake_mode))
    )
    return ToolResult(
        summary=f"Stage {step} '{stage.title}': {'PASS' if ok else 'FAIL'} - {msg}",
        ok=ok,
        tiles=[text_tile(f"tile-verify-{bundle_id}-{step}", f"Stage {step} check", msg)],
    )


def _get_properties(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    engine = PropertyEngine()
    props = engine.read_bundle_properties(bundle_path(ctx.conn, bundle_id))
    inst = resolve_instance(ctx.conn, args.get("instance"))
    snap = engine.load_snapshot(bundle_id, inst.id)
    live: dict[str, str | None] = {}
    note = "live values not read (simulated instance)"
    if not is_simulated(inst, ctx.fake_mode):
        live = run_async(engine.read_live_values(list(props), inst))
        note = "live values read from the instance"
    rows = [[k, v, _live_label(live, k)] for k, v in props.items()]
    tile = table_tile(
        f"tile-props-{bundle_id}",
        "System properties",
        ["Property", "Bundle value", "Live on instance"],
        rows,
    )
    return ToolResult(
        summary=f"{len(props)} propert(ies) in '{bundle_id}' ({note}); snapshot on "
        f"'{inst.name}': {'yes' if snap else 'no'}.",
        data={"properties": props, "live": live},
        tiles=[tile],
    )


def _live_label(live: dict[str, str | None], name: str) -> str:
    if not live:
        return "-"
    value = live.get(name)
    return "(not set)" if value is None else value


def _apply_properties(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    inst = resolve_instance(ctx.conn, args.get("instance"))
    res = run_async(
        PropertyEngine().apply_bundle_properties(
            bundle_id=bundle_id,
            bundle_path=bundle_path(ctx.conn, bundle_id),
            instance=inst,
            fake_mode=is_simulated(inst, ctx.fake_mode),
        )
    )
    return ToolResult(
        summary=f"Applied {res.applied_count} propert(ies) from '{bundle_id}' to '{inst.name}'.",
        ok=res.success,
        data={"applied": res.applied_count},
        tiles=[
            text_tile(f"tile-apply-{bundle_id}", "Properties applied", "\n".join(res.details[:8]))
        ],
    )


def _plan_restore(ctx: ToolContext, args: dict[str, Any]) -> str:
    return f"Restore original system properties for '{args['bundle_id']}' from the saved snapshot."


def _restore_properties(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    inst = resolve_instance(ctx.conn, args.get("instance"))
    res = run_async(
        PropertyEngine().restore_properties(
            bundle_id=bundle_id, instance=inst, fake_mode=is_simulated(inst, ctx.fake_mode)
        )
    )
    return ToolResult(
        summary=f"Restored {res.restored_count} propert(ies) for '{bundle_id}' on '{inst.name}'.",
        ok=res.success,
        data={"restored": res.restored_count},
        tiles=[
            text_tile(
                f"tile-restore-{bundle_id}", "Properties restored", "\n".join(res.details[:8])
            )
        ],
    )


register(
    ToolSpec(
        name="seed_bundle",
        description="Seed a bundle's sample records into an instance.",
        properties={"bundle_id": BUNDLE_ARG, "instance": _INST},
        required=["bundle_id"],
        handler=_seed,
        category="seed",
        cli_equivalent="demo seed",
    )
)
register(
    ToolSpec(
        name="rollback_seed",
        description="Delete the records created by a previous seed operation.",
        properties={"operation_id": {"type": "string"}},
        required=["operation_id"],
        handler=_rollback,
        category="seed",
        cli_equivalent="demo rollback",
        destructive=True,
        plan=_plan_rollback,
    )
)
register(
    ToolSpec(
        name="seed_history",
        description="Show recent seed operations and their status.",
        properties={"limit": {"type": "integer"}},
        handler=_seed_history,
        category="seed",
        cli_equivalent="demo seed-history",
    )
)
register(
    ToolSpec(
        name="verify_seed_operation",
        description=(
            "Check, read-only, that every record a seed operation created exists on the "
            "instance (by table and sys_id)."
        ),
        properties={"operation_id": {"type": "string"}},
        required=["operation_id"],
        handler=_verify_seed,
        category="seed",
        cli_equivalent="(API) verify seed records",
    )
)
register(
    ToolSpec(
        name="reset_demo",
        description="Tear a demo down: roll back its seed records and restore system properties.",
        properties={"bundle_id": BUNDLE_ARG, "instance": _INST},
        required=["bundle_id"],
        handler=_reset,
        category="seed",
        cli_equivalent="demo reset",
        destructive=True,
        plan=_plan_reset,
    )
)
register(
    ToolSpec(
        name="verify_stage",
        description="Verify live instance state for a walkthrough stage.",
        properties={"bundle_id": BUNDLE_ARG, "step_number": {"type": "integer"}, "instance": _INST},
        required=["bundle_id", "step_number"],
        handler=_verify_stage,
        category="bundle",
        cli_equivalent="demo verify-stage",
    )
)
register(
    ToolSpec(
        name="get_properties",
        description="Show a bundle's system properties and snapshot state.",
        properties={"bundle_id": BUNDLE_ARG, "instance": _INST},
        required=["bundle_id"],
        handler=_get_properties,
        category="properties",
        cli_equivalent="demo properties inspect",
    )
)
register(
    ToolSpec(
        name="apply_properties",
        description="Apply a bundle's system properties to an instance.",
        properties={"bundle_id": BUNDLE_ARG, "instance": _INST},
        required=["bundle_id"],
        handler=_apply_properties,
        category="properties",
        cli_equivalent="demo properties apply",
    )
)
register(
    ToolSpec(
        name="restore_properties",
        description="Restore original system properties from snapshot.",
        properties={"bundle_id": BUNDLE_ARG, "instance": _INST},
        required=["bundle_id"],
        handler=_restore_properties,
        category="properties",
        cli_equivalent="demo properties restore",
        destructive=True,
        plan=_plan_restore,
    )
)
