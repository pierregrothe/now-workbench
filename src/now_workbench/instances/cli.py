"""Instance CLI commands for now-workbench."""

import typer
from rich.console import Console
from rich.table import Table

from now_workbench.connectivity import check_and_record_instance
from now_workbench.db.models import (
    INSTANCE_PURPOSES,
    InstanceCreate,
    InstancePurpose,
    InstanceRecord,
    InstanceUpdate,
)
from now_workbench.db.repos.instances import InstanceRepository
from now_workbench.db.session import db_session


def _parse_purpose(value: str) -> InstancePurpose:
    """Validate a --purpose value against the allowed instance purposes."""
    for allowed in INSTANCE_PURPOSES:
        if value.strip().lower() == allowed:
            return allowed
    choices = ", ".join(INSTANCE_PURPOSES)
    raise typer.BadParameter(f"'{value}' is not one of: {choices}", param_hint="--purpose")


console = Console()
instance_app = typer.Typer(name="instance", help="Manage registered ServiceNow instances")


def format_instance_status(inst: InstanceRecord) -> str:
    """Format instance authentication status with rich badges."""
    if inst.status == "authenticated":
        return f"[bold green][OK] Authenticated[/bold green] [dim]({inst.username})[/dim]"
    if inst.status == "auth_failed":
        return "[bold red][FAIL] Auth Failed (401)[/bold red]"
    if inst.status == "unreachable":
        return "[bold red][FAIL] Unreachable[/bold red]"
    if inst.status in ("unknown", "", None):
        return "[yellow]? Untested[/yellow]"
    return f"[yellow]{inst.status}[/yellow]"


@instance_app.command("list")
def list_instances_cmd(
    check: bool = typer.Option(
        False,
        "--check",
        "-c",
        help="Probe live authentication for each instance before listing",
    ),
) -> None:
    """List all registered ServiceNow instances and authentication status."""
    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        instances = instance_repo.list_instances()

        if not instances:
            console.print("[yellow]No instances registered yet.[/yellow]")
            console.print("Add an instance via: [bold]workbench instance add <name> <url>[/bold]")
            return

        table = Table(title="Registered ServiceNow Instances", header_style="bold cyan")
        table.add_column("ID", style="bold white")
        table.add_column("Name")
        table.add_column("URL")
        table.add_column("User", style="cyan")
        table.add_column("Release", style="magenta")
        table.add_column("Default", style="green")
        table.add_column("Authentication Status")

        for inst in instances:
            if check:
                check_and_record_instance(conn, inst)
                refreshed = instance_repo.get_instance(inst.id)
                if refreshed:
                    inst = refreshed

            active_badge = (
                "[bold green]* ACTIVE[/bold green]" if inst.is_default else "[dim]--[/dim]"
            )
            status_badge = format_instance_status(inst)
            table.add_row(
                inst.id,
                inst.name,
                inst.url,
                inst.username,
                inst.release,
                active_badge,
                status_badge,
            )
    console.print(table)


@instance_app.command("add")
def add_instance_cmd(
    name: str = typer.Argument(..., help="Display name for this instance"),
    url: str = typer.Argument(..., help="Base URL of the ServiceNow instance"),
    instance_id: str | None = typer.Option(None, "--id", help="Explicit ID for the instance"),
    username: str = typer.Option("admin", "--username", "-u", help="ServiceNow username"),
    password: str = typer.Option("", "--password", "-p", help="ServiceNow password"),
    purpose: str = typer.Option(
        "demo",
        "--purpose",
        help="What you use it for: demo, development, test, or production",
    ),
    default: bool = typer.Option(False, "--default", "-d", help="Set as active default"),
) -> None:
    """Register a new ServiceNow instance (release and platform facts are detected)."""
    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        rec = instance_repo.add_instance(
            InstanceCreate(
                id=instance_id,
                name=name,
                url=url,
                username=username,
                password=password,
                auth_type="basic",
                purpose=_parse_purpose(purpose),
                is_default=default,
            )
        )
        status, msg, _ = check_and_record_instance(conn, rec)
        detected = instance_repo.get_instance(rec.id) or rec
    console.print(
        f"[green][OK][/green] Registered [bold]{rec.name}[/bold] (ID: [cyan]{rec.id}[/cyan])"
    )
    console.print(f"  Connection: {status} ({msg}); detected release: {detected.release}")
    if default:
        console.print(f"[green]*[/green] Set as active default instance: {rec.url}")


@instance_app.command("activate")
def activate_instance_cmd(
    instance_id: str = typer.Argument(..., help="Instance ID to mark as active default"),
) -> None:
    """Set an instance as the active default for tasks and customizations."""
    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        inst = instance_repo.get_instance(instance_id)
        if not inst:
            console.print(f"[red]Instance '{instance_id}' not found in registry.[/red]")
            raise typer.Exit(code=1)
        instance_repo.set_default_instance(instance_id)
    console.print(
        f"[green][OK][/green] Instance [bold]{inst.name}[/bold] ({inst.url}) is now ACTIVE."
    )


@instance_app.command("rename")
def rename_instance_cmd(
    instance_id: str = typer.Argument(..., help="Instance ID or name to rename"),
    new_name: str = typer.Argument(..., help="New display name for the instance"),
) -> None:
    """Rename a registered ServiceNow instance."""
    with db_session() as conn:
        rec = InstanceRepository(conn).update_instance(instance_id, InstanceUpdate(name=new_name))
        if not rec:
            console.print(f"[red]Instance '{instance_id}' not found in registry.[/red]")
            raise typer.Exit(code=1)
    console.print(f"[green][OK][/green] Instance renamed to [bold]{rec.name}[/bold]")


@instance_app.command("delete")
def delete_instance_cmd(
    instance_id: str = typer.Argument(..., help="Instance ID or name to delete"),
) -> None:
    """Delete a ServiceNow instance from the registry."""
    with db_session() as conn:
        ok = InstanceRepository(conn).delete_instance(instance_id)
        if not ok:
            console.print(f"[red]Instance '{instance_id}' not found in registry.[/red]")
            raise typer.Exit(code=1)
    console.print(f"[green][OK][/green] Instance [bold]{instance_id}[/bold] deleted.")


@instance_app.command("test")
def test_instance_cmd(
    instance_id: str = typer.Argument(
        None, help="Instance ID to test (defaults to all instances if omitted)"
    ),
) -> None:
    """Test connection and authentication to one or all registered instances."""
    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        targets: list[InstanceRecord] = []
        if instance_id:
            target = instance_repo.get_instance(instance_id)
            if not target:
                console.print(f"[red]Instance '{instance_id}' not found in registry.[/red]")
                raise typer.Exit(code=1)
            targets.append(target)
        else:
            targets = instance_repo.list_instances()

        if not targets:
            console.print("[red]No instance found to test. Register an instance first.[/red]")
            raise typer.Exit(code=1)

        console.print("[bold cyan]Testing ServiceNow Instance Authentication...[/bold cyan]\n")
        for inst in targets:
            status, msg, code = check_and_record_instance(conn, inst)
            if status == "authenticated":
                console.print(
                    f"  [green][OK][/green] [bold]{inst.name}[/bold] ({inst.url}): "
                    f"[green]Authenticated as '{inst.username}'[/green] (HTTP {code})"
                )
            elif status == "auth_failed":
                console.print(
                    f"  [red][FAIL][/red] [bold]{inst.name}[/bold] ({inst.url}): [red]{msg}[/red]"
                )
            else:
                console.print(
                    f"  [yellow][WARN][/yellow] [bold]{inst.name}[/bold] ({inst.url}): "
                    f"[yellow]{msg}[/yellow]"
                )
