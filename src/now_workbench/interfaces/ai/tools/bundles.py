"""Demo bundle catalog tools for the Otto agent (mirrors `workbench demo ...`/`template ...`)."""

import sqlite3
from pathlib import Path
from typing import Any

from now_workbench.domains.bundles import BundleManager
from now_workbench.domains.fluent import FluentEngine
from now_workbench.domains.runbooks import RunbookEngine
from now_workbench.domains.settings import PreferencesRepository
from now_workbench.domains.sharing import (
    ArtifactRepository,
    BundleAccess,
    ReadOnlyBundleError,
    delete_artifact_files,
    list_accessible,
    register_new_bundle,
    resolve_bundle,
)
from now_workbench.domains.synthesizer import (
    UseCaseSynthesisRequest,
    UseCaseSynthesizer,
    resolve_synthesis_release,
)
from now_workbench.domains.templates import (
    TemplateEngine,
    TemplateInstantiationRequest,
    TemplateRepository,
)
from now_workbench.interfaces.ai.tools.base import (
    BUNDLE_ARG,
    ToolContext,
    ToolResult,
    ToolSpec,
    register,
    table_tile,
    text_tile,
)
from now_workbench.platform.config.settings import settings
from now_workbench.platform.owner import current_owner


def bundle_access(conn: sqlite3.Connection, bundle_id: str, write: bool = False) -> BundleAccess:
    """Resolve a bundle the signed-in person may use (ADR-018) or raise ValueError."""
    try:
        return resolve_bundle(conn, str(bundle_id), write=write)
    except LookupError as exc:
        raise ValueError(f"Demo bundle '{bundle_id}' was not found.") from exc
    except ReadOnlyBundleError as exc:
        raise ValueError(str(exc)) from exc


def bundle_path(conn: sqlite3.Connection, bundle_id: str) -> Path:
    """Return the directory of a bundle the signed-in person may read."""
    return bundle_access(conn, bundle_id).path


def _mgr() -> BundleManager:
    return BundleManager(storage_dir=settings.get_bundles_dir())


def _bundle_actions(bundle_id: str) -> list[dict[str, Any]]:
    return [
        {"id": "seed", "label": "Seed to Instance", "variant": "primary", "bundle_id": bundle_id},
        {"id": "inspect", "label": "Open Artifact Library", "variant": "secondary"},
    ]


def _list_bundles(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundles = sorted(
        (
            BundleManager(storage_dir=a.root).inspect_bundle(a.path)
            for a in list_accessible(ctx.conn)
        ),
        key=lambda b: b.manifest.name,
    )
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
    access = bundle_access(ctx.conn, args["bundle_id"])
    info = BundleManager(storage_dir=access.root).inspect_bundle(access.path)
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
    source = bundle_access(ctx.conn, args["source_bundle_id"])
    info = _mgr().clone_bundle(
        source_id=args["source_bundle_id"],
        target_id=args["new_bundle_id"],
        target_name=args.get("new_name"),
        source_root=source.root,
    )
    register_new_bundle(ctx.conn, info.manifest.id, current_owner())
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
    access = bundle_access(ctx.conn, bundle_id)
    out = settings.workspace_dir / f"{bundle_id}.sn-demo.zip"
    BundleManager(storage_dir=access.root).export_bundle(bundle_id, out)
    return ToolResult(
        summary=f"Exported '{bundle_id}' to {out}.",
        data={"archive": str(out)},
        tiles=[text_tile(f"tile-export-{bundle_id}", "Bundle exported", f"Archive: {out}")],
    )


def _plan_delete_bundle(ctx: ToolContext, args: dict[str, Any]) -> str:
    return f"Permanently delete demo bundle '{args['bundle_id']}' and its media."


def _delete_bundle(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    bundle_access(ctx.conn, bundle_id, write=True)
    _mgr().delete_bundle(bundle_id)
    ArtifactRepository(ctx.conn).forget_artifact(bundle_id)
    delete_artifact_files(bundle_id)
    remaining = list_accessible(ctx.conn)
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
    prefs = PreferencesRepository(ctx.conn).get_workbench_preferences()
    req = UseCaseSynthesisRequest(
        use_case=str(args["use_case"]),
        customer_name=str(args.get("customer_name") or "Acme Global"),
        industry=str(args.get("industry") or "Enterprise IT"),
        sn_release=resolve_synthesis_release(ctx.conn, None, None),
        primary_color=prefs.default_brand_color,
    )
    result = UseCaseSynthesizer(bundles_dir=settings.get_bundles_dir()).synthesize(
        req, author_name=prefs.sc_author_name, scoped_prefix=prefs.default_scoped_prefix
    )
    register_new_bundle(ctx.conn, result.bundle_id, current_owner())
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
    guide = RunbookEngine().load_runbook(bundle_path(ctx.conn, bundle_id), bundle_id=bundle_id)
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
    tables = FluentEngine().load_bundle_schemas(bundle_path(ctx.conn, bundle_id))
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
    a = engine.load_bundle_schemas(bundle_path(ctx.conn, args["bundle_id"]))
    b = engine.load_bundle_schemas(bundle_path(ctx.conn, args["compare_bundle_id"]))
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
    templates = TemplateRepository(ctx.conn).list_templates()
    rows = [[t.id, t.name, t.base_bundle_id, ", ".join(t.parameters_schema)] for t in templates]
    tile = table_tile("tile-templates", "Templates", ["ID", "Name", "Base", "Parameters"], rows)
    return ToolResult(
        summary=f"{len(templates)} template(s) available.",
        data={"templates": [r[:3] for r in rows]},
        tiles=[tile],
    )


def _generate_template(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    templates = {t.id: t for t in TemplateRepository(ctx.conn).list_templates()}
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


def _update_bundle(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    bundle_id = str(args["bundle_id"])
    bundle_access(ctx.conn, bundle_id, write=True)
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
        properties={"bundle_id": BUNDLE_ARG},
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
            "source_bundle_id": BUNDLE_ARG,
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
        properties={"bundle_id": BUNDLE_ARG},
        required=["bundle_id"],
        handler=_export_bundle,
        category="bundle",
        cli_equivalent="demo export",
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
        properties={"bundle_id": BUNDLE_ARG},
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
        properties={"bundle_id": BUNDLE_ARG},
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
        properties={"bundle_id": BUNDLE_ARG, "compare_bundle_id": BUNDLE_ARG},
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
        name="update_bundle",
        description="Update metadata (name, description, tags) of a demonstration bundle.",
        properties={
            "bundle_id": BUNDLE_ARG,
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
        properties={"bundle_id": BUNDLE_ARG},
        required=["bundle_id"],
        handler=_delete_bundle,
        plan=_plan_delete_bundle,
        destructive=True,
        category="bundle",
        cli_equivalent="demo delete",
    )
)
