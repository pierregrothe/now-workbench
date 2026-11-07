# src/now_workbench/interfaces/cli/bundles.py
# The `workbench demo` command group: list, inspect, export, clone, runbook, seed, rollback.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Demo bundle commands (`workbench demo ...`)."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from now_workbench.domains.bundles import BundleManager
from now_workbench.domains.instances import InstanceRepository
from now_workbench.domains.runbooks import RunbookEngine
from now_workbench.domains.seed import SeedEngine, SeedRepository
from now_workbench.interfaces.cli.demos import (
    delete_capture_cmd,
    delete_demo_cmd,
    evaluate_demo_cmd,
    install_modules_cmd,
    list_captures_cmd,
    pipeline_demo_cmd,
    test_demo_cmd,
    update_capture_cmd,
    update_demo_cmd,
)
from now_workbench.interfaces.cli.fluent import fluent_app
from now_workbench.interfaces.cli.ids import safe_id
from now_workbench.interfaces.cli.properties import properties_app, reset_demo_cmd
from now_workbench.interfaces.cli.synthesizer import capture_demo_cmd, synthesize_demo_cmd
from now_workbench.platform.config.settings import settings
from now_workbench.platform.db.session import db_session

__all__ = [
    "clone_demo",
    "demo_app",
    "export_demo",
    "inspect_demo",
    "list_demos",
    "rollback_demo",
    "runbook_demo",
    "seed_demo",
    "seed_history_demo",
    "verify_stage_demo",
]

console = Console()


demo_app = typer.Typer(name="demo", help="Manage demonstration packages")


demo_app.add_typer(fluent_app)


demo_app.add_typer(properties_app)


demo_app.command(name="reset")(reset_demo_cmd)


demo_app.command(name="synthesize")(synthesize_demo_cmd)


demo_app.command(name="capture")(capture_demo_cmd)


demo_app.command(name="evaluate")(evaluate_demo_cmd)


demo_app.command(name="install-modules")(install_modules_cmd)


demo_app.command(name="test")(test_demo_cmd)


demo_app.command(name="pipeline")(pipeline_demo_cmd)


demo_app.command(name="delete")(delete_demo_cmd)


demo_app.command(name="update")(update_demo_cmd)


demo_app.command(name="list-captures")(list_captures_cmd)


demo_app.command(name="update-capture")(update_capture_cmd)


demo_app.command(name="delete-capture")(delete_capture_cmd)


@demo_app.command("list")
def list_demos() -> None:
    """List installed demonstration packages."""
    bundles_dir = settings.get_bundles_dir()
    mgr = BundleManager(storage_dir=bundles_dir)
    bundles = mgr.list_bundles()

    if not bundles:
        console.print("[yellow]No demonstration bundles found in storage.[/yellow]")
        console.print(f"Bundles directory: [dim]{bundles_dir}[/dim]")
        return

    table = Table(title="Installed Demonstration Packages", header_style="bold cyan")
    table.add_column("ID", style="bold white")
    table.add_column("Title")
    table.add_column("Version", style="green")
    table.add_column("Release", style="magenta")
    table.add_column("Fluent Files")
    table.add_column("Seed Records")

    for b in bundles:
        table.add_row(
            b.manifest.id,
            b.manifest.name,
            b.manifest.version,
            b.manifest.sn_release,
            str(len(b.fluent_files)),
            str(len(b.seed_files)),
        )
    console.print(table)


@demo_app.command("inspect")
def inspect_demo(bundle_id: str = typer.Argument(..., callback=safe_id)) -> None:
    """Inspect detailed metadata for a demonstration package."""
    bundles_dir = settings.get_bundles_dir()
    mgr = BundleManager(storage_dir=bundles_dir)
    bundle_path = bundles_dir / bundle_id
    if not bundle_path.exists():
        console.print(f"[red]Error: Bundle '{bundle_id}' not found.[/red]")
        raise typer.Exit(code=1)

    info = mgr.inspect_bundle(bundle_path)
    name = info.manifest.name
    ver = info.manifest.version
    header = f"[bold cyan]{name}[/bold cyan] ([green]v{ver}[/green])\n"
    console.print(
        Panel(
            header + f"[dim]{info.manifest.description}[/dim]\n\n"
            f"- Target Release: {info.manifest.sn_release}\n"
            f"- Required Plugins: {', '.join(info.manifest.required_plugins) or 'None'}\n"
            f"- Fluent Files: {len(info.fluent_files)}\n"
            f"- Seed Files: {len(info.seed_files)}\n"
            f"- Walkthrough Script: {'Available' if info.has_walkthrough else 'None'}",
            title=f"Demo: {bundle_id}",
            border_style="cyan",
        )
    )


@demo_app.command("export")
def export_demo(
    bundle_id: str = typer.Argument(..., callback=safe_id), output: Path = Path("demo.sn-demo.zip")
) -> None:
    """Export a demonstration package as a portable .sn-demo.zip archive."""
    bundles_dir = settings.get_bundles_dir()
    mgr = BundleManager(storage_dir=bundles_dir)
    try:
        archive = mgr.export_bundle(bundle_id, output)
        console.print(f"[green][OK] Exported bundle to:[/green] {archive.resolve()}")
    except Exception as e:
        console.print(f"[red]Failed to export bundle: {e}[/red]")
        raise typer.Exit(code=1)


@demo_app.command("clone")
def clone_demo(
    source_id: str = typer.Argument(
        ..., callback=safe_id, help="Source demo bundle ID to clone from"
    ),
    target_id: str = typer.Argument(..., callback=safe_id, help="New target bundle ID/slug"),
    name: str = typer.Option(None, "--name", "-n", help="Optional display name for cloned demo"),
) -> None:
    """Clone an existing demo bundle to customize for a customer without modifying baseline."""
    bundles_dir = settings.get_bundles_dir()
    mgr = BundleManager(storage_dir=bundles_dir)
    try:
        info = mgr.clone_bundle(source_id=source_id, target_id=target_id, target_name=name)
        console.print(
            f"[green][OK][/green] Cloned demo bundle [bold]{source_id}[/bold] -> "
            f"[bold]{info.manifest.id}[/bold] ('{info.manifest.name}')"
        )
    except Exception as exc:
        console.print(f"[red]Error cloning bundle: {exc}[/red]")
        raise typer.Exit(code=1)


@demo_app.command("runbook")
def runbook_demo(
    bundle_id: str = typer.Argument(
        ..., callback=safe_id, help="Demo bundle ID to inspect runbook for"
    ),
) -> None:
    """Display demonstration stages, personas, and talking points from guide.md."""
    bundles_dir = settings.get_bundles_dir()
    bundle_path = bundles_dir / bundle_id
    if not bundle_path.exists():
        console.print(f"[red]Error: Bundle '{bundle_id}' not found in {bundles_dir}[/red]")
        raise typer.Exit(code=1)

    engine = RunbookEngine()
    guide = engine.load_runbook(bundle_path, bundle_id=bundle_id)
    if not guide:
        console.print(f"[yellow]No walkthrough guide found for bundle '{bundle_id}'.[/yellow]")
        return

    console.print(
        Panel(
            f"[bold cyan]{guide.title}[/bold cyan]\n"
            f"[dim]{guide.narrative}[/dim]\n\n"
            f"- Stages: {len(guide.stages)}\n"
            f"- Personas: {', '.join(p.name for p in guide.personas) or 'None'}",
            title=f"Runbook: {bundle_id}",
            border_style="cyan",
        )
    )

    for stage in guide.stages:
        persona_tag = f" [dim](as {stage.persona})[/dim]" if stage.persona else ""
        console.print(
            f"\n[bold green]Stage {stage.step_number}: {stage.title}[/bold green]{persona_tag}"
        )
        if stage.instructions:
            console.print("  [bold]Actions:[/bold]")
            for inst in stage.instructions:
                console.print(f"    - {inst}")
        if stage.talking_points:
            console.print("  [bold yellow]Talking Points:[/bold yellow]")
            for tp in stage.talking_points:
                console.print(f"    * {tp}")
        if stage.target_table:
            console.print(f"  [dim]Platform Target: {stage.target_table}[/dim]")


@demo_app.command("verify-stage")
def verify_stage_demo(
    bundle_id: str = typer.Argument(..., callback=safe_id, help="Demo bundle ID"),
    step_number: int = typer.Argument(..., help="Stage number to verify"),
    instance_id: str = typer.Option(None, "--instance", "-i", help="Target instance ID"),
    fake: bool = typer.Option(False, "--fake", help="Simulate Table API verification"),
) -> None:
    """Verify live ServiceNow instance state for a demonstration stage."""
    bundles_dir = settings.get_bundles_dir()
    bundle_path = bundles_dir / bundle_id
    if not bundle_path.exists():
        console.print(f"[red]Error: Bundle '{bundle_id}' not found in {bundles_dir}[/red]")
        raise typer.Exit(code=1)

    engine = RunbookEngine()
    guide = engine.load_runbook(bundle_path, bundle_id=bundle_id)
    if not guide:
        console.print(f"[red]No walkthrough guide found for bundle '{bundle_id}'.[/red]")
        raise typer.Exit(code=1)

    stage = next((s for s in guide.stages if s.step_number == step_number), None)
    if not stage:
        console.print(f"[red]Stage {step_number} not found in runbook.[/red]")
        raise typer.Exit(code=1)

    with db_session() as conn:
        inst = InstanceRepository(conn).resolve(instance_id)
    if not inst:
        console.print("[red]Target instance not found in registry.[/red]")
        raise typer.Exit(code=1)

    ok, msg = asyncio.run(engine.verify_stage(stage, inst, fake_mode=fake))
    if ok:
        console.print(f"[green][OK][/green] {msg}")
    else:
        console.print(f"[red][FAIL][/red] {msg}")
        raise typer.Exit(code=1)


@demo_app.command("seed")
def seed_demo(
    bundle_id: str = typer.Argument(
        ..., callback=safe_id, help="Demo bundle ID to seed records from"
    ),
    instance_id: str = typer.Option(None, "--instance", "-i", help="Target instance ID"),
    fake: bool = typer.Option(False, "--fake", help="Run with in-memory simulated Table API"),
) -> None:
    """Seed sample data records into target ServiceNow instance."""
    bundles_dir = settings.get_bundles_dir()
    bundle_path = bundles_dir / bundle_id
    if not bundle_path.exists():
        console.print(f"[red]Error: Bundle '{bundle_id}' not found in {bundles_dir}[/red]")
        raise typer.Exit(code=1)

    console.print(f"Seeding records from [bold]{bundle_id}[/bold]...")
    with db_session() as conn:
        engine = SeedEngine(conn=conn, fake_mode=fake)
        try:
            op = asyncio.run(engine.load_and_seed(bundle_id, bundle_path, instance_id=instance_id))
            msg = (
                f"[green][OK][/green] Created {len(op.created_records)} records! "
                f"(ID: [cyan]{op.id}[/cyan])"
            )
            console.print(msg)
            for rec in op.created_records:
                row_msg = f"  * Table: [cyan]{rec.table}[/cyan] sys_id: [dim]{rec.sys_id}[/dim]"
                console.print(row_msg)
        except Exception as exc:
            console.print(f"[red]Seed operation failed: {exc}[/red]")
            raise typer.Exit(code=1)


@demo_app.command("rollback")
def rollback_demo(
    operation_id: str = typer.Argument(..., help="Seed operation ID to rollback"),
    fake: bool = typer.Option(False, "--fake", help="Run with simulated Table API"),
) -> None:
    """Roll back (delete) records created in a previous seed operation."""
    console.print(f"Rolling back operation [cyan]{operation_id}[/cyan]...")
    with db_session() as conn:
        engine = SeedEngine(conn=conn, fake_mode=fake)
        try:
            deleted_count, errors = asyncio.run(engine.rollback(operation_id))
            console.print(f"[green][OK][/green] Deleted {deleted_count} seed records.")
            if errors:
                for err in errors:
                    console.print(f"  [yellow]![/yellow] {err}")
        except Exception as exc:
            console.print(f"[red]Rollback failed: {exc}[/red]")
            raise typer.Exit(code=1)


@demo_app.command("seed-history")
def seed_history_demo(
    limit: int = typer.Option(20, "--limit", "-l", help="Max operations to show"),
) -> None:
    """Show audit history of demo seed runs and rollback states."""
    with db_session() as conn:
        ops = SeedRepository(conn).list_seed_operations(limit=limit)

    if not ops:
        console.print("[yellow]No seed operations recorded yet.[/yellow]")
        return

    table = Table(title="Demo Seed Operations Audit History", header_style="bold cyan")
    table.add_column("Operation ID", style="bold white")
    table.add_column("Bundle", style="cyan")
    table.add_column("Instance", style="magenta")
    table.add_column("Records", style="green")
    table.add_column("Status")
    table.add_column("Created At", style="dim")

    for op in ops:
        status_style = (
            "[green]COMPLETED[/green]"
            if op.status == "completed"
            else f"[dim]{op.status.upper()}[/dim]"
        )
        table.add_row(
            op.id,
            op.bundle_id,
            op.instance_id,
            str(len(op.created_records)),
            status_style,
            op.created_at[:19].replace("T", " "),
        )
    console.print(table)
