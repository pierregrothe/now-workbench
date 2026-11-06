"""Demo bundle catalog tools for the Otto agent (mirrors `workbench demo ...`/`template ...`)."""

from pathlib import Path
from typing import Any

from now_workbench.ai.tools.base import (
    ToolContext,
    ToolResult,
    ToolSpec,
    media_tile,
    register,
    resolve_instance,
    run_async,
    table_tile,
    text_tile,
)
from now_workbench.bundles.manager import BundleManager
from now_workbench.bundles.pipeline import DemoPipelineEngine
from now_workbench.capture.engine import PlaywrightCaptureEngine
from now_workbench.capture.models import CaptureRequest
from now_workbench.config.paths import safe_child
from now_workbench.config.settings import settings
from now_workbench.db import TemplateInstantiationRequest
from now_workbench.fluent.engine import FluentEngine
from now_workbench.runbooks.engine import RunbookEngine
from now_workbench.synthesizer.engine import UseCaseSynthesizer
from now_workbench.synthesizer.models import UseCaseSynthesisRequest
from now_workbench.synthesizer.release import resolve_synthesis_release
from now_workbench.templates import TemplateEngine

_BUNDLE = {"type": "string", "description": "Demo bundle id (slug)"}


def bundle_path(bundle_id: str) -> Path:
    """Resolve an installed bundle directory or raise ValueError."""
    target = safe_child(settings.get_bundles_dir(), str(bundle_id))
    if not target.exists():
        raise ValueError(f"Demo bundle '{bundle_id}' was not found.")
    return target


def _mgr() -> BundleManager:
    return BundleManager(storage_dir=settings.get_bundles_dir())


def _bundle_actions(bundle_id: str) -> list[dict[str, Any]]:
    return [
        {"id": "seed", "label": "Seed to Instance", "variant": "primary", "bundle_id": bundle_id},
        {"id": "inspect", "label": "Open Artifact Library", "variant": "secondary"},
    ]


def _list_bundles(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundles = _mgr().list_bundles()
    rows = [
        [b.manifest.id, b.manifest.name, b.manifest.sn_release, len(b.fluent_files)]
        for b in bundles
    ]
    tile = table_tile("tile-bundles", "Demo bundles", ["ID", "Name", "Release", "Tables"], rows)
    return ToolResult(
        summary=f"{len(bundles)} demo bundle(s) installed.",
        data={"bundles": [r[:3] for r in rows]},
        tiles=[tile],
    )


def _inspect_bundle(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    path = bundle_path(args["bundle_id"])
    info = _mgr().inspect_bundle(path)
    m = info.manifest
    body = (
        f"{m.description or 'No description.'}\n"
        f"Release: {m.sn_release} | Version: {m.version} | Author: {m.author or 'n/a'}\n"
        f"Fluent files: {len(info.fluent_files)} | Seed files: {len(info.seed_files)} | "
        f"Walkthrough: {'yes' if info.has_walkthrough else 'no'} | "
        f"Properties: {len(info.sys_properties)}"
    )
    return ToolResult(
        summary=f"Bundle '{m.name}' ({m.id}): {len(info.fluent_files)} tables, "
        f"{len(info.seed_files)} seed files, {len(info.sys_properties)} properties.",
        data=info.model_dump(mode="json"),
        tiles=[text_tile(f"tile-inspect-{m.id}", m.name, body, _bundle_actions(m.id))],
    )


def _clone_bundle(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    info = _mgr().clone_bundle(
        source_id=args["source_bundle_id"],
        target_id=args["new_bundle_id"],
        target_name=args.get("new_name"),
    )
    return ToolResult(
        summary=f"Cloned '{args['source_bundle_id']}' to '{info.manifest.id}'.",
        data={"bundle_id": info.manifest.id},
        tiles=[
            text_tile(
                f"tile-clone-{info.manifest.id}",
                "Bundle cloned",
                f"{info.manifest.name} ({info.manifest.id}) is ready to customize.",
                _bundle_actions(info.manifest.id),
            )
        ],
    )


def _export_bundle(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    bundle_path(bundle_id)
    out = settings.workspace_dir / f"{bundle_id}.sn-demo.zip"
    _mgr().export_bundle(bundle_id, out)
    return ToolResult(
        summary=f"Exported '{bundle_id}' to {out}.",
        data={"archive": str(out)},
        tiles=[text_tile(f"tile-export-{bundle_id}", "Bundle exported", f"Archive: {out}")],
    )


def _plan_delete_bundle(ctx: ToolContext, args: dict[str, Any]) -> str:
    return f"Permanently delete demo bundle '{args['bundle_id']}' and its media."


def _delete_bundle(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    _mgr().delete_bundle(bundle_id)
    remaining = _mgr().list_bundles()
    return ToolResult(
        summary=f"Deleted bundle '{bundle_id}'. {len(remaining)} bundle(s) remain.",
        data={"remaining": len(remaining)},
        tiles=[
            text_tile(
                f"tile-deleted-{bundle_id}",
                "Bundle deleted",
                f"'{bundle_id}' was removed. {len(remaining)} bundle(s) remain.",
                [{"id": "show_bundles", "label": "Show Recipes", "variant": "primary"}],
            )
        ],
    )


def _synthesize(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    prefs = ctx.repo.get_workbench_preferences()
    req = UseCaseSynthesisRequest(
        use_case=str(args["use_case"]),
        customer_name=str(args.get("customer_name") or "Acme Global"),
        industry=str(args.get("industry") or "Enterprise IT"),
        sn_release=resolve_synthesis_release(ctx.repo, None, None),
        primary_color=prefs.default_brand_color,
    )
    result = UseCaseSynthesizer(bundles_dir=settings.get_bundles_dir()).synthesize(
        req, author_name=prefs.sc_author_name, scoped_prefix=prefs.default_scoped_prefix
    )
    return ToolResult(
        summary=f"Synthesized bundle '{result.bundle_id}' for {result.customer_name} "
        f"({len(result.seed_records)} seed records, table {result.fluent_table_name}).",
        data={"bundle_id": result.bundle_id},
        tiles=[
            text_tile(
                f"tile-synth-{result.bundle_id}",
                result.title,
                f"Customer: {result.customer_name} | Industry: {result.industry}\n"
                f"Fluent table: {result.fluent_table_name}\n"
                f"Seed records: {len(result.seed_records)}",
                _bundle_actions(result.bundle_id),
            )
        ],
    )


def _get_runbook(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    guide = RunbookEngine().load_runbook(bundle_path(bundle_id), bundle_id=bundle_id)
    if not guide:
        return ToolResult(summary=f"'{bundle_id}' has no walkthrough guide.", ok=False)
    rows = [[s.step_number, s.title, s.persona or "-", len(s.talking_points)] for s in guide.stages]
    tile = table_tile(
        f"tile-runbook-{bundle_id}", guide.title, ["Step", "Stage", "Persona", "Talking pts"], rows
    )
    return ToolResult(
        summary=f"Runbook '{guide.title}': {len(guide.stages)} stage(s), "
        f"{len(guide.personas)} persona(s).",
        data={"stages": [r[:3] for r in rows]},
        tiles=[tile],
    )


def _fluent_schema(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    tables = FluentEngine().load_bundle_schemas(bundle_path(bundle_id))
    rows = [[t.name, t.label, ", ".join(c.name for c in t.columns)] for t in tables]
    tile = table_tile(
        f"tile-fluent-{bundle_id}", "Fluent tables", ["Table", "Label", "Columns"], rows
    )
    return ToolResult(
        summary=f"{len(tables)} Fluent table(s) in '{bundle_id}'.",
        data={"tables": [r[:2] for r in rows]},
        tiles=[tile],
    )


def _fluent_diff(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    engine = FluentEngine()
    a = engine.load_bundle_schemas(bundle_path(args["bundle_id"]))
    b = engine.load_bundle_schemas(bundle_path(args["compare_bundle_id"]))
    diff = engine.compute_diff(a, b)
    rows = [["added", ", ".join(diff.added_tables) or "-"]]
    rows.append(["removed", ", ".join(diff.removed_tables) or "-"])
    rows += [[f"modified {t}", "; ".join(c)] for t, c in diff.modified_tables.items()]
    tile = table_tile("tile-fluent-diff", "Fluent schema diff", ["Change", "Detail"], rows)
    return ToolResult(
        summary="Schemas are identical." if diff.identical else "Schemas differ.",
        data=diff.model_dump(),
        tiles=[tile],
    )


def _list_templates(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    templates = ctx.repo.list_templates()
    rows = [[t.id, t.name, t.base_bundle_id, ", ".join(t.parameters_schema)] for t in templates]
    tile = table_tile("tile-templates", "Templates", ["ID", "Name", "Base", "Parameters"], rows)
    return ToolResult(
        summary=f"{len(templates)} template(s) available.",
        data={"templates": [r[:3] for r in rows]},
        tiles=[tile],
    )


def _generate_template(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    templates = {t.id: t for t in ctx.repo.list_templates()}
    tid = str(args["template_id"])
    if tid not in templates:
        raise ValueError(f"Template '{tid}' not found.")
    req = TemplateInstantiationRequest(
        target_bundle_id=str(args["new_bundle_id"]),
        customer_name=str(args["customer_name"]),
        primary_color=str(args.get("primary_color") or "#23a17e"),
    )
    out = TemplateEngine(
        bundles_dir=settings.get_bundles_dir(), output_dir=settings.workspace_dir
    ).instantiate(templates[tid].base_bundle_id, req)
    return ToolResult(
        summary=(
            f"Generated '{req.target_bundle_id}' for {req.customer_name} from template '{tid}'."
        ),
        data={"bundle_path": str(out)},
        tiles=[
            text_tile(
                f"tile-gen-{req.target_bundle_id}",
                "Template generated",
                f"{req.customer_name}: {out}",
            )
        ],
    )


def _capture(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    prefs = ctx.repo.get_workbench_preferences()
    inst = resolve_instance(ctx.repo, args.get("instance"))
    bundle_id = str(args.get("bundle_id") or "sample-ai-assistant")
    req = CaptureRequest(
        bundle_id=bundle_id,
        instance_id=inst.id,
        target_path=str(
            args.get("target_path") or "/now/nav/ui/classic/params/target/incident_list.do"
        ),
        media_type=str(args.get("media_type") or prefs.capture_default_media_type),
        label=str(args.get("label") or "Instance State Capture"),
        viewport_width=prefs.capture_viewport_width,
        viewport_height=prefs.capture_viewport_height,
        fake_mode=prefs.capture_fake_mode or ctx.fake_mode,
    )
    art = run_async(
        PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir()).capture(
            req,
            instance_url=inst.url,
            wait_timeout_ms=prefs.capture_wait_timeout_ms,
            username=inst.username,
            password=inst.password,
        )
    )
    return ToolResult(
        summary=f"Captured {art.media_type} '{art.filename}' for bundle '{bundle_id}'.",
        data={"filename": art.filename, "url": art.url},
        tiles=[
            media_tile(
                f"tile-capture-{art.id}",
                f"{art.media_type.title()} Proof: {bundle_id}",
                art.url,
                media_type=art.media_type,
                label=f"{art.label} ({art.target_path})",
                actions=[
                    {"id": "inspect", "label": "Open Artifacts", "variant": "secondary"},
                ],
            )
        ],
    )


def _evaluate_demo(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args.get("bundle_id") or "")
    inst = resolve_instance(ctx.repo, args.get("instance"))
    engine = DemoPipelineEngine(bundles_dir=settings.get_bundles_dir(), repo=ctx.repo)
    res = engine.evaluate_bundle(bundle_id, inst, fake_mode=ctx.fake_mode)

    columns = ["Requirement", "Details", "Status"]
    n_rec = res.seed_records_count
    n_tbl = len(res.target_tables)
    rows = [
        [
            "Modules",
            f"Required: {len(res.required_plugins)} | Missing: {len(res.missing_plugins)}",
            "Satisfied" if not res.missing_plugins else "Missing Modules",
        ],
        ["Configurations", f"{res.system_properties_count} system properties", "Ready"],
        ["Demo Data", f"{n_rec} records across {n_tbl} tables", "Ready"],
        ["Runbook Script", f"{res.walkthrough_stages_count} demonstration stages", "Ready"],
        [
            "Overall Readiness",
            f"Target: {inst.name} ({res.sn_release})",
            "Ready" if res.is_ready else "Modules Needed",
        ],
    ]

    tile = table_tile(f"tile-eval-{bundle_id}", f"Readiness Scorecard: {bundle_id}", columns, rows)
    status_msg = (
        "ready to deploy" if res.is_ready else f"{len(res.missing_plugins)} module(s) missing"
    )
    return ToolResult(
        summary=f"Evaluated demo '{bundle_id}' for {inst.name}: {status_msg}.",
        data=res.model_dump(),
        tiles=[tile],
    )


def _install_demo_modules(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args.get("bundle_id") or "")
    inst = resolve_instance(ctx.repo, args.get("instance"))
    engine = DemoPipelineEngine(bundles_dir=settings.get_bundles_dir(), repo=ctx.repo)
    installed = engine.install_required_modules(bundle_id, inst, fake_mode=ctx.fake_mode)

    if not installed:
        return ToolResult(
            summary=f"All required modules for '{bundle_id}' are active on {inst.name}.",
            tiles=[
                text_tile(
                    f"tile-mod-{bundle_id}",
                    "Modules Status",
                    "All required modules are active.",
                )
            ],
        )

    lines = [f"- {p.plugin_id}: {p.plugin_name} (active)" for p in installed]
    tile = text_tile(
        f"tile-mod-{bundle_id}",
        f"Activated {len(installed)} Module(s) on {inst.name}",
        "\n".join(lines),
    )
    return ToolResult(
        summary=(
            f"Activated {len(installed)} required module(s) for '{bundle_id}' on {inst.name}."
        ),
        data={"installed_count": len(installed), "modules": [p.plugin_id for p in installed]},
        tiles=[tile],
    )


def _test_demo_script(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args.get("bundle_id") or "")
    inst = resolve_instance(ctx.repo, args.get("instance"))
    engine = DemoPipelineEngine(bundles_dir=settings.get_bundles_dir(), repo=ctx.repo)
    res = run_async(engine.test_demo_script(bundle_id, inst, fake_mode=ctx.fake_mode))

    columns = ["Stage #", "Title", "Target Table", "Result"]
    rows = [
        [str(s.step_number), s.title, s.target_table or "-", "PASS" if s.passed else "FAIL"]
        for s in res.stages
    ]

    tile = table_tile(f"tile-test-{bundle_id}", f"Demo Script Test: {bundle_id}", columns, rows)
    pass_summary = f"{res.passed_stages}/{res.total_stages} stages passed"
    return ToolResult(
        summary=f"Verified demo script '{bundle_id}' on {inst.name}: {pass_summary}.",
        data=res.model_dump(),
        tiles=[tile],
    )


def _run_demo_pipeline(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args.get("bundle_id") or "")
    inst = resolve_instance(ctx.repo, args.get("instance"))
    no_video = bool(args.get("no_video", False))
    engine = DemoPipelineEngine(bundles_dir=settings.get_bundles_dir(), repo=ctx.repo)
    summary = run_async(
        engine.run_full_pipeline(
            bundle_id=bundle_id,
            instance=inst,
            fake_mode=ctx.fake_mode,
            record_video=not no_video,
        )
    )

    tiles = []
    if summary.video_proof_url:
        stg_cnt = summary.tested_stages_count
        tiles.append(
            media_tile(
                f"tile-proof-{bundle_id}",
                f"Video Proof: {bundle_id}",
                summary.video_proof_url,
                media_type="video",
                label=f"Verified execution proof on {inst.name} ({stg_cnt} stages tested)",
                actions=[
                    {"id": "inspect", "label": "Open Artifacts", "variant": "secondary"},
                ],
            )
        )
    else:
        tiles.append(
            text_tile(
                f"tile-pipe-{bundle_id}",
                "Pipeline Execution Summary",
                summary.message,
            )
        )

    return ToolResult(
        summary=summary.message,
        data=summary.model_dump(),
        tiles=tiles,
    )


def _update_bundle(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    tags_arg = args.get("tags")
    tags_list = (
        [t.strip() for t in tags_arg.split(",") if t.strip()]
        if isinstance(tags_arg, str)
        else tags_arg
    )
    info = _mgr().update_bundle_manifest(
        bundle_id=bundle_id,
        name=args.get("name"),
        description=args.get("description"),
        tags=tags_list,
    )
    tags_str = ", ".join(info.manifest.tags)
    return ToolResult(
        summary=f"Updated bundle '{bundle_id}': {info.manifest.name}.",
        data=info.model_dump(),
        tiles=[
            text_tile(
                f"tile-update-{bundle_id}",
                "Bundle Updated",
                f"{info.manifest.name}\n{info.manifest.description or ''}\nTags: {tags_str}",
            )
        ],
    )


register(
    ToolSpec(
        name="list_bundles",
        description="List installed demo bundles.",
        properties={},
        handler=_list_bundles,
        category="bundle",
        cli_equivalent="demo list",
    )
)
register(
    ToolSpec(
        name="inspect_bundle",
        description="Show metadata for a demo bundle.",
        properties={"bundle_id": _BUNDLE},
        required=["bundle_id"],
        handler=_inspect_bundle,
        category="bundle",
        cli_equivalent="demo inspect",
    )
)
register(
    ToolSpec(
        name="clone_bundle",
        description="Clone a bundle to customize without changing the original.",
        properties={
            "source_bundle_id": _BUNDLE,
            "new_bundle_id": {"type": "string"},
            "new_name": {"type": "string"},
        },
        required=["source_bundle_id", "new_bundle_id"],
        handler=_clone_bundle,
        category="bundle",
        cli_equivalent="demo clone",
    )
)
register(
    ToolSpec(
        name="export_bundle",
        description="Export a bundle as a portable .sn-demo.zip archive.",
        properties={"bundle_id": _BUNDLE},
        required=["bundle_id"],
        handler=_export_bundle,
        category="bundle",
        cli_equivalent="demo export",
    )
)
register(
    ToolSpec(
        name="delete_bundle",
        description="Delete a demo bundle.",
        properties={"bundle_id": _BUNDLE},
        required=["bundle_id"],
        handler=_delete_bundle,
        category="bundle",
        cli_equivalent="(API) DELETE /api/demos/{id}",
        destructive=True,
        plan=_plan_delete_bundle,
    )
)
register(
    ToolSpec(
        name="synthesize_bundle",
        description="Generate a new demo bundle (Fluent schema, seed data, properties, narrative).",
        properties={
            "use_case": {"type": "string"},
            "customer_name": {"type": "string"},
            "industry": {"type": "string"},
        },
        required=["use_case"],
        handler=_synthesize,
        category="bundle",
        cli_equivalent="demo synthesize",
    )
)
register(
    ToolSpec(
        name="get_runbook",
        description="Show a bundle's walkthrough stages and personas.",
        properties={"bundle_id": _BUNDLE},
        required=["bundle_id"],
        handler=_get_runbook,
        category="bundle",
        cli_equivalent="demo runbook",
    )
)
register(
    ToolSpec(
        name="fluent_schema",
        description="Show the Fluent SDK tables declared in a bundle.",
        properties={"bundle_id": _BUNDLE},
        required=["bundle_id"],
        handler=_fluent_schema,
        category="fluent",
        cli_equivalent="demo fluent inspect",
    )
)
register(
    ToolSpec(
        name="fluent_diff",
        description="Diff Fluent schemas between two bundles.",
        properties={"bundle_id": _BUNDLE, "compare_bundle_id": _BUNDLE},
        required=["bundle_id", "compare_bundle_id"],
        handler=_fluent_diff,
        category="fluent",
        cli_equivalent="demo fluent diff",
    )
)
register(
    ToolSpec(
        name="list_templates",
        description="List customization templates.",
        properties={},
        handler=_list_templates,
        category="template",
        cli_equivalent="template list, template inspect",
    )
)
register(
    ToolSpec(
        name="generate_from_template",
        description="Generate a customer-tailored bundle from a template.",
        properties={
            "template_id": {"type": "string"},
            "new_bundle_id": {"type": "string"},
            "customer_name": {"type": "string"},
            "primary_color": {"type": "string"},
        },
        required=["template_id", "new_bundle_id", "customer_name"],
        handler=_generate_template,
        category="template",
        cli_equivalent="template generate",
    )
)
register(
    ToolSpec(
        name="capture_media",
        description="Capture a screenshot or video of an instance page for a bundle.",
        properties={
            "instance": {"type": "string"},
            "bundle_id": _BUNDLE,
            "target_path": {"type": "string"},
            "media_type": {"type": "string", "enum": ["screenshot", "video"]},
            "label": {"type": "string"},
        },
        handler=_capture,
        category="bundle",
        cli_equivalent="demo capture",
    )
)
register(
    ToolSpec(
        name="evaluate_demo",
        description="Evaluate bundle prerequisites (modules, properties, data) on an instance.",
        properties={"bundle_id": _BUNDLE, "instance": {"type": "string"}},
        required=["bundle_id"],
        handler=_evaluate_demo,
        category="bundle",
        cli_equivalent="demo evaluate",
    )
)
register(
    ToolSpec(
        name="install_demo_modules",
        description="Install or activate ServiceNow plugins and modules required by a demo bundle.",
        properties={"bundle_id": _BUNDLE, "instance": {"type": "string"}},
        required=["bundle_id"],
        handler=_install_demo_modules,
        category="bundle",
        cli_equivalent="demo install-modules",
    )
)
register(
    ToolSpec(
        name="test_demo_script",
        description="Execute automated runbook test verification across all demo stages.",
        properties={"bundle_id": _BUNDLE, "instance": {"type": "string"}},
        required=["bundle_id"],
        handler=_test_demo_script,
        category="bundle",
        cli_equivalent="demo test",
    )
)
register(
    ToolSpec(
        name="run_demo_pipeline",
        description=(
            "Execute full demo lifecycle: evaluate, install modules, configure, seed, "
            "test, and prove."
        ),
        properties={
            "bundle_id": _BUNDLE,
            "instance": {"type": "string"},
            "no_video": {"type": "boolean"},
        },
        required=["bundle_id"],
        handler=_run_demo_pipeline,
        category="bundle",
        cli_equivalent="demo pipeline",
    )
)
register(
    ToolSpec(
        name="update_bundle",
        description="Update metadata (name, description, tags) of a demonstration bundle.",
        properties={
            "bundle_id": _BUNDLE,
            "name": {"type": "string"},
            "description": {"type": "string"},
            "tags": {"type": "string"},
        },
        required=["bundle_id"],
        handler=_update_bundle,
        category="bundle",
        cli_equivalent="demo update",
    )
)
register(
    ToolSpec(
        name="delete_bundle",
        description="Permanently delete a demonstration bundle and all its artifacts.",
        properties={"bundle_id": _BUNDLE},
        required=["bundle_id"],
        handler=_delete_bundle,
        plan=_plan_delete_bundle,
        destructive=True,
        category="bundle",
        cli_equivalent="demo delete",
    )
)
