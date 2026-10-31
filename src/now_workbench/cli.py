"""CLI entrypoint for now-workbench."""

import asyncio
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from now_workbench import __version__
from now_workbench.bundles.manager import BundleManager
from now_workbench.bundles.pipeline_cli import (
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
from now_workbench.config.cli import config_app
from now_workbench.config.settings import settings
from now_workbench.db.session import db_session
from now_workbench.fluent.cli import fluent_app
from now_workbench.instances.cli import format_instance_status, instance_app
from now_workbench.properties.cli import properties_app, reset_demo_cmd
from now_workbench.remediation import (
    RemediationPlan,
    execute_remediation,
    inspect_remediation_needs,
)
from now_workbench.runbooks.engine import RunbookEngine
from now_workbench.sdk.runner import NowSdkRunner
from now_workbench.seed.engine import SeedEngine
from now_workbench.synthesizer.cli import capture_demo_cmd, synthesize_demo_cmd
from now_workbench.templates.cli import template_app

_format_instance_status = format_instance_status

app = typer.Typer(
    name="workbench",
    help="AI-native developer & demonstration workbench for the ServiceNow SDK",
    add_completion=False,
)
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

app.add_typer(demo_app)
app.add_typer(instance_app)
app.add_typer(template_app)
app.add_typer(config_app)

console = Console()


def _render_doctor_table(probe: dict[str, str | bool]) -> None:
    """Render the diagnostics table for doctor."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_column("Details")

    # Node.js
    if probe["node_available"]:
        table.add_row("Node.js", "[green][OK] Available[/green]", str(probe["node_path"]))
    else:
        table.add_row(
            "Node.js", "[red][X] Missing[/red]", "Install Node.js 20+ LTS to run @servicenow/sdk"
        )

    # now-sdk
    if probe["now_sdk_available"]:
        table.add_row("ServiceNow SDK", "[green][OK] Available[/green]", str(probe["now_sdk_path"]))
    else:
        table.add_row(
            "ServiceNow SDK",
            "[yellow]! Not in PATH[/yellow]",
            "Run 'workbench doctor --fix' or 'npm install -g @servicenow/sdk'",
        )

    # Multi-Instance Registry
    with db_session() as repo:
        instances = repo.list_instances()
        active_inst = repo.get_default_instance()

    if instances:
        auth_count = sum(1 for inst in instances if inst.status == "authenticated")
        active_label = f"Active: '{active_inst.name}'" if active_inst else "No active default"
        auth_note = f"{auth_count}/{len(instances)} Authenticated"
        inst_summary = f"[green][OK] {len(instances)} registered[/green] ({auth_note})"
        inst_details = (
            f"{active_label} ({active_inst.url})"
            if active_inst
            else "Run 'workbench instance list'"
        )
        table.add_row("Instance Registry", inst_summary, inst_details)
    else:
        table.add_row(
            "Instance Registry",
            "[yellow]! 0 registered[/yellow]",
            "Register instances with 'workbench instance add' or via Admin UI",
        )

    # Claude API / Otto
    claude_key = os.environ.get("WORKBENCH_ANTHROPIC_API_KEY", settings.anthropic_api_key)
    if claude_key:
        table.add_row("Otto (Claude API)", "[green][OK] Connected[/green]", settings.claude_model)
    else:
        table.add_row(
            "Otto (Claude API)",
            "[yellow]! Simulation[/yellow]",
            "Set WORKBENCH_ANTHROPIC_API_KEY for live Claude streaming",
        )

    console.print(table)


def _render_remediation_summary(plan: RemediationPlan) -> None:
    """Render remediation recommendations when issues are detected."""
    if not plan.has_issues:
        console.print("[green]System is fully configured and ready.[/green]")
        return

    console.print("\n[bold yellow]Remediation Recommendations:[/bold yellow]")
    if plan.needs_sdk_install:
        console.print("  * [cyan]ServiceNow SDK[/cyan]: Run [bold]workbench doctor --fix[/bold]")
        console.print("    (Installs non-root to ~/.now-workbench/sdk or use -g)")
    if plan.needs_data_dir or plan.needs_bundles_dir or plan.needs_workspace_dir:
        console.print("  * [cyan]Directories[/cyan]: Storage folders created with --fix")
    if plan.needs_env_file:
        console.print("  * [cyan]Configuration[/cyan]: .env initialized with --fix")
    console.print(
        "\nRun [bold green]workbench doctor --fix[/bold green] to automatically remediate.\n"
    )


def _run_remediation_cli(install_mode: str) -> None:
    """Execute remediation tasks from the CLI."""
    console.print("\n[bold cyan]Executing Automated Remediation...[/bold cyan]")
    actions = asyncio.run(execute_remediation(install_mode=install_mode))
    for act in actions:
        if act.success:
            console.print(f"  [green][OK][/green] {act.component}: {act.details}")
        else:
            console.print(f"  [red][FAIL][/red] {act.component}: {act.details}")


@app.command()
def version() -> None:
    """Print the workbench version."""
    console.print(f"[bold cyan]now-workbench[/bold cyan] version [green]{__version__}[/green]")


@app.command()
def doctor(
    fix: bool = typer.Option(
        False,
        "--fix",
        "-f",
        help="Automatically remediate detected missing toolchain components or directories",
    ),
    install_mode: str = typer.Option(
        "user",
        "--mode",
        "-m",
        help="SDK install mode: 'user' (~/.now-workbench/sdk, no root needed) or 'global'",
    ),
) -> None:
    """Run diagnostics on local toolchain, ServiceNow SDK, and environment."""
    console.print(
        Panel(
            "[bold white]now-workbench Diagnostic Health Check[/bold white]",
            border_style="cyan",
        )
    )

    runner = NowSdkRunner(now_sdk_bin=settings.now_sdk_bin, node_bin=settings.node_bin)
    probe = runner.probe_environment()
    _render_doctor_table(probe)

    plan = inspect_remediation_needs()
    if fix and plan.has_issues:
        _run_remediation_cli(install_mode)
        console.print("\n[bold cyan]Post-Remediation Verification:[/bold cyan]")
        re_probe = runner.probe_environment()
        _render_doctor_table(re_probe)
    elif plan.has_issues:
        _render_remediation_summary(plan)


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
def inspect_demo(bundle_id: str) -> None:
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
def export_demo(bundle_id: str, output: Path = Path("demo.sn-demo.zip")) -> None:
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
    source_id: str = typer.Argument(..., help="Source demo bundle ID to clone from"),
    target_id: str = typer.Argument(..., help="New target bundle ID/slug"),
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
    bundle_id: str = typer.Argument(..., help="Demo bundle ID to inspect runbook for"),
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
    bundle_id: str = typer.Argument(..., help="Demo bundle ID"),
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

    with db_session() as repo:
        inst = repo.get_instance(instance_id) if instance_id else repo.get_default_instance()
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
    bundle_id: str = typer.Argument(..., help="Demo bundle ID to seed records from"),
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
    with db_session() as repo:
        engine = SeedEngine(repository=repo, fake_mode=fake)
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
    with db_session() as repo:
        engine = SeedEngine(repository=repo, fake_mode=fake)
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
    with db_session() as repo:
        ops = repo.list_seed_operations(limit=limit)

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


@app.command()
def serve(
    host: str = typer.Option(settings.host, "--host", "-h", help="Bind host"),
    port: int = typer.Option(settings.port, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on changes"),
) -> None:
    """Start the FastAPI backend server and serve the ServiceNow Lux web UI."""
    import uvicorn

    console.print(
        Panel(
            f"[bold white]Starting now-workbench server[/bold white]\n"
            f"Web UI: [bold cyan]http://{host}:{port}[/bold cyan]\n"
            f"API Docs: [dim]http://{host}:{port}/docs[/dim]",
            border_style="cyan",
        )
    )
    uvicorn.run("now_workbench.api.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
