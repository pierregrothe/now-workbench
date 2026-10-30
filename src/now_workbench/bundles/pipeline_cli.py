"""CLI commands for demo evaluation, module installation, testing, and full pipeline execution."""

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from now_workbench.bundles.manager import BundleManager
from now_workbench.bundles.pipeline import DemoPipelineEngine
from now_workbench.capture.engine import PlaywrightCaptureEngine
from now_workbench.config.settings import settings
from now_workbench.db.models import InstanceRecord
from now_workbench.db.repository import DatabaseRepository
from now_workbench.db.session import db_session

console = Console()


def _resolve_instance(repo: DatabaseRepository, instance_id: str | None) -> InstanceRecord:
    inst = repo.get_instance(instance_id) if instance_id else repo.get_default_instance()
    if not inst:
        console.print("[red]Error: Target instance not found in registry.[/red]")
        raise typer.Exit(code=1)
    return inst


def evaluate_demo_cmd(
    bundle_id: str = typer.Argument(..., help="Demo bundle ID to evaluate"),
    instance_id: str = typer.Option(None, "--instance", "-i", help="Target instance ID"),
    fake: bool = typer.Option(False, "--fake", help="Offline simulation mode"),
) -> None:
    """Evaluate prerequisites (modules, properties, seed data) needed for a demonstration."""
    bundles_dir = settings.get_bundles_dir()
    with db_session() as repo:
        inst = _resolve_instance(repo, instance_id)
        engine = DemoPipelineEngine(bundles_dir=bundles_dir, repo=repo)
        try:
            res = engine.evaluate_bundle(bundle_id, inst, fake_mode=fake)
        except Exception as exc:
            console.print(f"[red]Evaluation error: {exc}[/red]")
            raise typer.Exit(code=1)

    table = Table(title=f"Demo Readiness Scorecard: {bundle_id} -> {inst.name}", show_header=True)
    table.add_column("Requirement Category", style="bold cyan")
    table.add_column("Details", style="white")
    table.add_column("Status", style="bold")

    plug_status = (
        "[green]SATISFIED[/green]" if not res.missing_plugins else "[yellow]MISSING[/yellow]"
    )
    plug_detail = (
        f"Required: {len(res.required_plugins)} ({', '.join(res.required_plugins) or 'None'})\n"
        f"Missing: {len(res.missing_plugins)} ({', '.join(res.missing_plugins) or 'None'})"
    )
    table.add_row("ServiceNow Modules", plug_detail, plug_status)

    prop_detail = f"{res.system_properties_count} system properties in sys_properties.json"
    table.add_row("Configurations", prop_detail, "[green]READY[/green]")

    seed_detail = f"{res.seed_records_count} records across tables: {', '.join(res.target_tables)}"
    table.add_row("Demonstration Data", seed_detail, "[green]READY[/green]")

    walk_detail = f"{res.walkthrough_stages_count} walkthrough demonstration stages"
    table.add_row("Runbook Script", walk_detail, "[green]READY[/green]")

    overall = (
        "[bold green]READY TO DEPLOY[/bold green]"
        if res.is_ready
        else "[bold yellow]MODULES REQUIRED[/bold yellow]"
    )
    table.add_row("Overall Readiness", f"Target ServiceNow Release: {res.sn_release}", overall)

    console.print(table)


def install_modules_cmd(
    bundle_id: str = typer.Argument(..., help="Demo bundle ID"),
    instance_id: str = typer.Option(None, "--instance", "-i", help="Target instance ID"),
    fake: bool = typer.Option(False, "--fake", help="Offline simulation mode"),
) -> None:
    """Install or activate all ServiceNow plugins and modules required by a demo."""
    bundles_dir = settings.get_bundles_dir()
    with db_session() as repo:
        inst = _resolve_instance(repo, instance_id)
        engine = DemoPipelineEngine(bundles_dir=bundles_dir, repo=repo)
        try:
            installed = engine.install_required_modules(bundle_id, inst, fake_mode=fake)
        except Exception as exc:
            console.print(f"[red]Plugin installation error: {exc}[/red]")
            raise typer.Exit(code=1)

    if not installed:
        console.print(
            f"[green]All required modules for '{bundle_id}' are active on {inst.name}.[/green]"
        )
        return

    mod_list = "\n".join(f"- {p.plugin_id}: {p.plugin_name}" for p in installed)
    console.print(
        Panel(
            f"[bold green]Activated {len(installed)} module(s) on {inst.name}:[/bold green]\n"
            + mod_list,
            title="Modules Installed",
            border_style="green",
        )
    )


def test_demo_cmd(
    bundle_id: str = typer.Argument(..., help="Demo bundle ID to test"),
    instance_id: str = typer.Option(None, "--instance", "-i", help="Target instance ID"),
    fake: bool = typer.Option(False, "--fake", help="Offline simulation mode"),
) -> None:
    """Execute end-to-end runbook test verification across all demonstration stages."""
    bundles_dir = settings.get_bundles_dir()
    with db_session() as repo:
        inst = _resolve_instance(repo, instance_id)
        engine = DemoPipelineEngine(bundles_dir=bundles_dir, repo=repo)
        try:
            res = asyncio.run(engine.test_demo_script(bundle_id, inst, fake_mode=fake))
        except Exception as exc:
            console.print(f"[red]Test execution error: {exc}[/red]")
            raise typer.Exit(code=1)

    table = Table(title=f"Demo Script Test Results: {bundle_id} on {inst.name}", show_header=True)
    table.add_column("Stage #", justify="center", style="bold")
    table.add_column("Stage Title", style="cyan")
    table.add_column("Target Table", style="dim")
    table.add_column("Result", style="bold")

    for s in res.stages:
        status = "[green]PASS[/green]" if s.passed else "[red]FAIL[/red]"
        table.add_row(str(s.step_number), s.title, s.target_table or "-", status)

    console.print(table)
    if res.all_passed:
        console.print(
            f"[bold green]All {res.total_stages} stages passed verification![/bold green]"
        )
    else:
        console.print(f"[bold red]Passed {res.passed_stages}/{res.total_stages} stages.[/bold red]")
        raise typer.Exit(code=1)


def pipeline_demo_cmd(
    bundle_id: str = typer.Argument(..., help="Demo bundle ID to run full pipeline for"),
    instance_id: str = typer.Option(None, "--instance", "-i", help="Target instance ID"),
    no_video: bool = typer.Option(False, "--no-video", help="Skip video proof recording"),
    fake: bool = typer.Option(False, "--fake", help="Offline simulation mode"),
) -> None:
    """Execute full demo lifecycle: evaluate, install modules, configure, seed, test, and prove."""
    bundles_dir = settings.get_bundles_dir()
    with db_session() as repo:
        inst = _resolve_instance(repo, instance_id)
        engine = DemoPipelineEngine(bundles_dir=bundles_dir, repo=repo)
        try:
            summary = asyncio.run(
                engine.run_full_pipeline(
                    bundle_id=bundle_id,
                    instance=inst,
                    fake_mode=fake,
                    record_video=not no_video,
                )
            )
        except Exception as exc:
            console.print(f"[red]Pipeline execution error: {exc}[/red]")
            raise typer.Exit(code=1)

    table = Table(title=f"Demonstration Pipeline Execution Summary: {bundle_id}", show_header=True)
    table.add_column("Stage", style="bold cyan")
    table.add_column("Outcome", style="white")

    n_mods = len(summary.installed_modules)
    table.add_row("Target Instance", f"{inst.name} ({inst.url})")
    table.add_row("Module Setup", f"Activated {n_mods} missing module(s)")
    table.add_row(
        "Configurations",
        f"Applied {summary.applied_properties_count} system properties (backed up in WAL)",
    )
    table.add_row(
        "Demo Data", f"Seeded {summary.seeded_records_count} records across target tables"
    )
    stg_result = "PASS" if summary.test_passed else "FAIL"
    table.add_row("Runbook Script", f"Verified {summary.tested_stages_count} stages ({stg_result})")
    if summary.video_proof_url:
        table.add_row("Video Proof", f"{summary.video_proof_filename} -> {summary.video_proof_url}")

    console.print(table)
    if summary.video_proof_url:
        console.print(
            f"\n[bold green]Watch video proof in the UI at: {summary.video_proof_url}[/bold green]"
        )


def delete_demo_cmd(
    bundle_id: str = typer.Argument(..., help="Demo bundle ID to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Bypass confirmation prompt"),
) -> None:
    """Delete a demonstration bundle package."""
    mgr = BundleManager(storage_dir=settings.get_bundles_dir())
    if not force:
        msg = f"Are you sure you want to permanently delete bundle '{bundle_id}'?"
        if not typer.confirm(msg):
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return
    try:
        mgr.delete_bundle(bundle_id)
        console.print(f"[green][OK][/green] Demonstration bundle '{bundle_id}' deleted.")
    except Exception as exc:
        console.print(f"[red]Error deleting bundle: {exc}[/red]")
        raise typer.Exit(code=1)


def update_demo_cmd(
    bundle_id: str = typer.Argument(..., help="Demo bundle ID to update"),
    name: str | None = typer.Option(None, "--name", help="New title for the demo bundle"),
    description: str | None = typer.Option(None, "--description", "--desc", help="New description"),
    tags: str | None = typer.Option(None, "--tags", help="Comma-separated tags"),
) -> None:
    """Update metadata fields in a demonstration bundle's manifest.json."""
    mgr = BundleManager(storage_dir=settings.get_bundles_dir())
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    try:
        info = mgr.update_bundle_manifest(
            bundle_id=bundle_id,
            name=name,
            description=description,
            tags=tag_list,
        )
        console.print(
            f"[green][OK][/green] Updated demo bundle '{bundle_id}': "
            f"[bold]{info.manifest.name}[/bold]"
        )
    except Exception as exc:
        console.print(f"[red]Error updating bundle: {exc}[/red]")
        raise typer.Exit(code=1)


def list_captures_cmd(
    bundle_id: str = typer.Argument(..., help="Demo bundle ID to list captures for"),
) -> None:
    """List all screenshots and videos recorded for a demo bundle."""
    engine = PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir())
    captures = engine.list_captures(bundle_id)
    if not captures:
        console.print(f"[yellow]No captures found for bundle '{bundle_id}'.[/yellow]")
        return

    table = Table(title=f"Media Captures: {bundle_id}", show_header=True)
    table.add_column("Filename", style="bold cyan")
    table.add_column("Type", style="bold")
    table.add_column("Label / Caption", style="white")
    table.add_column("Engine", style="dim")
    table.add_column("URL", style="green")

    for c in captures:
        table.add_row(c.filename, c.media_type.upper(), c.label or "-", c.engine, c.url)

    console.print(table)


def update_capture_cmd(
    bundle_id: str = typer.Argument(..., help="Demo bundle ID"),
    filename: str = typer.Argument(..., help="Capture filename (.png or .webm)"),
    label: str = typer.Option(..., "--label", "-l", help="New caption or label"),
) -> None:
    """Update label or caption of a screenshot or video artifact."""
    engine = PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir())
    try:
        updated = engine.update_capture(bundle_id, filename, label=label)
        console.print(
            f"[green][OK][/green] Updated capture '{filename}' label to: "
            f"[bold]{updated.label}[/bold]"
        )
    except Exception as exc:
        console.print(f"[red]Error updating capture: {exc}[/red]")
        raise typer.Exit(code=1)


def delete_capture_cmd(
    bundle_id: str = typer.Argument(..., help="Demo bundle ID"),
    filename: str = typer.Argument(..., help="Capture filename (.png or .webm) to delete"),
) -> None:
    """Delete a recorded screenshot or video artifact file."""
    engine = PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir())
    try:
        engine.delete_capture(bundle_id, filename)
        console.print(
            f"[green][OK][/green] Deleted capture artifact '{filename}' from bundle '{bundle_id}'."
        )
    except Exception as exc:
        console.print(f"[red]Error deleting capture: {exc}[/red]")
        raise typer.Exit(code=1)
