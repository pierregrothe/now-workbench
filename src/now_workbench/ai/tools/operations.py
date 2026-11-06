"""Demo lifecycle tools for the Otto agent (seed, rollback, properties, stage verification)."""

from typing import Any

from now_workbench.ai.tools.base import (
    ToolContext,
    ToolResult,
    ToolSpec,
    register,
    resolve_instance,
    run_async,
    table_tile,
    text_tile,
)
from now_workbench.ai.tools.bundles import bundle_path
from now_workbench.db import InstanceRecord
from now_workbench.properties.engine import PropertyEngine
from now_workbench.runbooks.engine import RunbookEngine
from now_workbench.seed.engine import SeedEngine

_BUNDLE = {"type": "string", "description": "Demo bundle id (slug)"}
_INST = {"type": "string", "description": "Instance id/name; defaults to the default instance"}


def _is_fake(ctx: ToolContext, inst: InstanceRecord) -> bool:
    return ctx.fake_mode or inst.url.startswith("fake://")


def _seed(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    inst = resolve_instance(ctx.repo, args.get("instance"))
    engine = SeedEngine(repository=ctx.repo, fake_mode=_is_fake(ctx, inst))
    op = run_async(engine.load_and_seed(bundle_id, bundle_path(bundle_id), instance_id=inst.id))
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
    op = ctx.repo.get_seed_operation(str(args["operation_id"]))
    if not op:
        return f"Seed operation '{args['operation_id']}' was not found."
    return (
        f"Delete {len(op.created_records)} record(s) created by seed operation "
        f"{op.id} (bundle {op.bundle_id})."
    )


def _rollback(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    op_id = str(args["operation_id"])
    op = ctx.repo.get_seed_operation(op_id)
    fake = ctx.fake_mode
    if op:
        target = ctx.repo.get_instance(op.instance_id)
        fake = fake or bool(target and target.url.startswith("fake://"))
    engine = SeedEngine(repository=ctx.repo, fake_mode=fake)
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
    ops = ctx.repo.list_seed_operations(limit=int(args.get("limit") or 10))
    rows = [[o.id, o.bundle_id, o.instance_id, o.status, len(o.created_records)] for o in ops]
    tile = table_tile(
        "tile-seed-history",
        "Seed history",
        ["Operation", "Bundle", "Instance", "Status", "Records"],
        rows,
    )
    return ToolResult(
        summary=f"{len(ops)} seed operation(s) on record.",
        data={"operations": [r[:4] for r in rows]},
        tiles=[tile],
    )


def _plan_reset(ctx: ToolContext, args: dict[str, Any]) -> str:
    return (
        f"Reset demo '{args['bundle_id']}': roll back its seed records and restore the "
        "original system properties."
    )


def _reset(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    bundle_path(bundle_id)
    inst = resolve_instance(ctx.repo, args.get("instance"))
    fake = _is_fake(ctx, inst)
    seed_engine = SeedEngine(repository=ctx.repo, fake_mode=fake)
    ops = [
        o
        for o in ctx.repo.list_seed_operations(limit=100)
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
    guide = RunbookEngine().load_runbook(bundle_path(bundle_id), bundle_id=bundle_id)
    if not guide:
        return ToolResult(summary=f"'{bundle_id}' has no walkthrough guide.", ok=False)
    step = int(args["step_number"])
    stage = next((s for s in guide.stages if s.step_number == step), None)
    if not stage:
        return ToolResult(summary=f"Stage {step} not found in '{bundle_id}'.", ok=False)
    inst = resolve_instance(ctx.repo, args.get("instance"))
    ok, msg = run_async(RunbookEngine().verify_stage(stage, inst, fake_mode=_is_fake(ctx, inst)))
    return ToolResult(
        summary=f"Stage {step} '{stage.title}': {'PASS' if ok else 'FAIL'} - {msg}",
        ok=ok,
        tiles=[text_tile(f"tile-verify-{bundle_id}-{step}", f"Stage {step} check", msg)],
    )


def _get_properties(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    engine = PropertyEngine()
    props = engine.read_bundle_properties(bundle_path(bundle_id))
    inst = resolve_instance(ctx.repo, args.get("instance"))
    snap = engine.load_snapshot(bundle_id, inst.id)
    tile = table_tile(
        f"tile-props-{bundle_id}",
        "System properties",
        ["Property", "Value"],
        [[k, v] for k, v in props.items()],
    )
    return ToolResult(
        summary=f"{len(props)} propert(ies) in '{bundle_id}'; snapshot on '{inst.name}': "
        f"{'yes' if snap else 'no'}.",
        data={"properties": props},
        tiles=[tile],
    )


def _apply_properties(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    inst = resolve_instance(ctx.repo, args.get("instance"))
    res = run_async(
        PropertyEngine().apply_bundle_properties(
            bundle_id=bundle_id,
            bundle_path=bundle_path(bundle_id),
            instance=inst,
            fake_mode=_is_fake(ctx, inst),
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
    inst = resolve_instance(ctx.repo, args.get("instance"))
    res = run_async(
        PropertyEngine().restore_properties(
            bundle_id=bundle_id, instance=inst, fake_mode=_is_fake(ctx, inst)
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
        properties={"bundle_id": _BUNDLE, "instance": _INST},
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
        name="reset_demo",
        description="Tear a demo down: roll back its seed records and restore system properties.",
        properties={"bundle_id": _BUNDLE, "instance": _INST},
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
        properties={"bundle_id": _BUNDLE, "step_number": {"type": "integer"}, "instance": _INST},
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
        properties={"bundle_id": _BUNDLE, "instance": _INST},
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
        properties={"bundle_id": _BUNDLE, "instance": _INST},
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
        properties={"bundle_id": _BUNDLE, "instance": _INST},
        required=["bundle_id"],
        handler=_restore_properties,
        category="properties",
        cli_equivalent="demo properties restore",
        destructive=True,
        plan=_plan_restore,
    )
)
