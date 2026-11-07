# src/now_workbench/interfaces/ai/tools/demos.py
# Otto tools for a demo's lifecycle: evaluate, install modules, test, run the pipeline, capture.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Demo lifecycle tools (pipeline, module install, script test, captures)."""

import base64
from pathlib import Path
from typing import Any

from now_workbench.domains.capture import CaptureRequest, PlaywrightCaptureEngine
from now_workbench.domains.demos import DemoPipelineEngine
from now_workbench.domains.instances import is_simulated
from now_workbench.domains.settings import PreferencesRepository
from now_workbench.interfaces.ai.tools.base import (
    BUNDLE_ARG,
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
from now_workbench.interfaces.ai.tools.bundles import bundle_access
from now_workbench.platform.config.settings import settings

__all__ = []


_MAX_IMAGE_BYTES = 3_500_000


def _capture(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    prefs = PreferencesRepository(ctx.conn).get_workbench_preferences()
    inst = resolve_instance(ctx.conn, args.get("instance"))
    bundle_id = str(args.get("bundle_id") or "sample-ai-assistant")
    bundle_access(ctx.conn, bundle_id, write=True)
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
        fake_mode=is_simulated(inst, prefs.capture_fake_mode or ctx.fake_mode),
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
    simulated = art.engine == "playwright-simulated"
    quality = (
        "SIMULATED placeholder (capture fake mode is on), not a real view of the instance"
        if simulated
        else "live capture; the browser signed in and the page was not a sign-in screen"
    )
    picture = Path(art.file_path)
    if art.media_type == "video":
        picture = picture.with_suffix(".png")
    images = (
        [base64.standard_b64encode(picture.read_bytes()).decode("ascii")]
        if not simulated and picture.exists() and picture.stat().st_size < _MAX_IMAGE_BYTES
        else []
    )
    return ToolResult(
        summary=(
            f"Captured {art.media_type} '{art.filename}' for bundle '{bundle_id}' ({quality})."
            + (" The image is attached: check it shows what was asked." if images else "")
        ),
        images=images,
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
    inst = resolve_instance(ctx.conn, args.get("instance"))
    root = bundle_access(ctx.conn, bundle_id).root
    engine = DemoPipelineEngine(bundles_dir=root, conn=ctx.conn)
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
            f"Target: {inst.name} ({inst.release}, needs {res.min_release} or later)",
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
    inst = resolve_instance(ctx.conn, args.get("instance"))
    root = bundle_access(ctx.conn, bundle_id).root
    engine = DemoPipelineEngine(bundles_dir=root, conn=ctx.conn)
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
    inst = resolve_instance(ctx.conn, args.get("instance"))
    root = bundle_access(ctx.conn, bundle_id).root
    engine = DemoPipelineEngine(bundles_dir=root, conn=ctx.conn)
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
    inst = resolve_instance(ctx.conn, args.get("instance"))
    no_video = bool(args.get("no_video", False))
    bundle_access(ctx.conn, bundle_id, write=True)
    engine = DemoPipelineEngine(bundles_dir=settings.get_bundles_dir(), conn=ctx.conn)
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


register(
    ToolSpec(
        name="capture_media",
        description="Capture a screenshot or video of an instance page for a bundle.",
        properties={
            "instance": {"type": "string"},
            "bundle_id": BUNDLE_ARG,
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
        properties={"bundle_id": BUNDLE_ARG, "instance": {"type": "string"}},
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
        properties={"bundle_id": BUNDLE_ARG, "instance": {"type": "string"}},
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
        properties={"bundle_id": BUNDLE_ARG, "instance": {"type": "string"}},
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
            "bundle_id": BUNDLE_ARG,
            "instance": {"type": "string"},
            "no_video": {"type": "boolean"},
        },
        required=["bundle_id"],
        handler=_run_demo_pipeline,
        category="bundle",
        cli_equivalent="demo pipeline",
    )
)
