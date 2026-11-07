"""CLI entrypoint for now-workbench."""

import asyncio
import os
from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from now_workbench import __version__
from now_workbench.domains.identity import operator_owner
from now_workbench.domains.instances import InstanceRepository
from now_workbench.domains.settings import PreferencesRepository
from now_workbench.domains.sharing import sync_registry
from now_workbench.interfaces.cli.bundles import demo_app
from now_workbench.interfaces.cli.config import config_app
from now_workbench.interfaces.cli.instances import format_instance_status, instance_app
from now_workbench.interfaces.cli.templates import template_app
from now_workbench.platform.config.settings import settings
from now_workbench.platform.db.session import db_session
from now_workbench.platform.owner import owner_scope
from now_workbench.platform.remediation import (
    RemediationPlan,
    execute_remediation,
    inspect_remediation_needs,
)
from now_workbench.platform.s3 import S3Target, put_object
from now_workbench.platform.sdk.runner import NowSdkRunner

_format_instance_status = format_instance_status

app = typer.Typer(
    name="workbench",
    help="AI-native developer & demonstration workbench for the ServiceNow SDK",
    add_completion=False,
)


app.add_typer(demo_app)
app.add_typer(instance_app)
app.add_typer(template_app)
app.add_typer(config_app)

console = Console()


@app.callback()
def _act_as_operator(ctx: typer.Context) -> None:
    """Run every command as the first administrator, or the local operator (ADR-018)."""
    with db_session() as conn:
        owner = operator_owner(conn, local_mode=not settings.get_access_audience())
    ctx.with_resource(owner_scope(owner))
    ctx.call_on_close(lambda: _register_new_bundles(owner))


def _register_new_bundles(owner: str) -> None:
    """Bundles a command put on disk (clone, synthesize, import) belong to the operator."""
    with db_session() as conn:
        sync_registry(conn, owner)


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
    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        instances = instance_repo.list_instances()
        active_inst = instance_repo.get_default_instance()

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
    if not claude_key:
        try:
            with db_session() as conn:
                claude_key = PreferencesRepository(conn).get_decrypted_anthropic_api_key()
        except Exception:
            pass
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


def _snapshot() -> bytes:
    """A consistent copy of the live database, through SQLite's online backup."""
    import sqlite3
    import tempfile

    from now_workbench.platform.db.session import get_db_path

    with tempfile.TemporaryDirectory() as tmp:
        snapshot = Path(tmp) / "snapshot.db"
        source = sqlite3.connect(get_db_path())
        target = sqlite3.connect(snapshot)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        return snapshot.read_bytes()


def _s3_target() -> S3Target:
    """The backup bucket from settings; every part must be set."""
    target = S3Target(
        bucket=settings.backup_s3_bucket,
        region=settings.backup_s3_region,
        access_key_id=settings.backup_s3_access_key_id,
        secret_access_key=settings.backup_s3_secret_access_key,
        endpoint=settings.backup_s3_endpoint,
    )
    if not (target.bucket and target.access_key_id and target.secret_access_key):
        raise typer.BadParameter(
            "set WORKBENCH_BACKUP_S3_BUCKET, WORKBENCH_BACKUP_S3_ACCESS_KEY_ID and "
            "WORKBENCH_BACKUP_S3_SECRET_ACCESS_KEY first",
            param_hint="--s3",
        )
    return target


@app.command()
def backup(
    out: str = typer.Option("-", "--out", "-o", help="Destination file, or - for stdout"),
    s3: bool = typer.Option(False, "--s3", help="Upload to the configured S3 bucket instead"),
) -> None:
    """Write a consistent snapshot of the database (credentials stay sealed).

    The master key is NOT included: keep it separately, or the snapshot cannot be decrypted.
    Example on the server: docker exec now-workbench workbench backup > workbench.db
    With --s3 the snapshot goes to s3://<bucket>/<prefix>workbench-<UTC time>.db.
    """
    import sys
    from datetime import UTC, datetime

    if s3:
        target = _s3_target()
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        data = _snapshot()
        try:
            where = put_object(target, f"{settings.backup_s3_prefix}workbench-{stamp}.db", data)
        except (RuntimeError, ValueError, httpx.HTTPError) as exc:
            console.print(f"[bold red]Backup upload failed:[/bold red] {exc}")
            raise typer.Exit(code=1) from exc
        console.print(f"[green]Backup uploaded:[/green] {where} ({len(data)} bytes)")
        return
    data = _snapshot()
    if out == "-":
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
        return
    Path(out).write_bytes(data)
    console.print(f"[green]Backup written:[/green] {out} ({len(data)} bytes)")


@app.command()
def serve(
    host: str = typer.Option(settings.host, "--host", "-h", help="Bind host"),
    port: int = typer.Option(settings.port, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on changes"),
) -> None:
    """Start the FastAPI backend server and serve the ServiceNow Lux web UI."""
    import os

    import uvicorn

    from now_workbench.interfaces.api.access import AccessValidator
    from now_workbench.interfaces.api.guard import assert_safe_binding

    try:
        assert_safe_binding(
            host, AccessValidator(settings.get_access_team_domain(), settings.get_access_audience())
        )
    except RuntimeError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=1) from exc
    os.environ["WORKBENCH_HOST"] = host

    console.print(
        Panel(
            f"[bold white]Starting now-workbench server[/bold white]\n"
            f"Web UI: [bold cyan]http://{host}:{port}[/bold cyan]\n"
            f"API Docs: [dim]http://{host}:{port}/docs[/dim]",
            border_style="cyan",
        )
    )
    uvicorn.run("now_workbench.interfaces.api.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
