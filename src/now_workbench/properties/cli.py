"""CLI subcommands for system property management and demo reset."""

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from now_workbench.config.settings import settings
from now_workbench.db.models import InstanceRecord
from now_workbench.db.repository import DatabaseRepository
from now_workbench.db.session import db_session
from now_workbench.properties.engine import PropertyEngine
from now_workbench.seed.engine import SeedEngine

properties_app = typer.Typer(
    name="properties",
    help="Inspect, apply, and restore demonstration system properties",
)
console = Console()


def _get_target_instance(
    repo: DatabaseRepository, instance_id: str | None
) -> InstanceRecord | None:
    """Resolve target instance from repository."""
    if instance_id:
        return repo.get_instance(instance_id)
    return repo.get_default_instance()


@properties_app.command("inspect")
def inspect_properties(
    bundle_id: str = typer.Argument(..., help="Demo bundle identifier"),
) -> None:
    """Inspect system properties configured in a demo bundle."""
    bundle_path = settings.get_bundles_dir() / bundle_id
    if not bundle_path.exists():
        console.print(f"[bold red]Error:[/bold red] Demo bundle '{bundle_id}' not found.")
        raise typer.Exit(code=1)

    engine = PropertyEngine()
    props = engine.read_bundle_properties(bundle_path)
    if not props:
        console.print(f"[yellow]No system properties configured for '{bundle_id}'.[/yellow]")
        return

    table = Table(title=f"System Properties for '{bundle_id}'", show_header=True)
    table.add_column("Property Name", style="cyan")
    table.add_column("Configured Value", style="green")

    for k, v in sorted(props.items()):
        table.add_row(k, v)

    console.print(table)


@properties_app.command("apply")
def apply_properties(
    bundle_id: str = typer.Argument(..., help="Demo bundle identifier"),
    instance: str | None = typer.Option(
        None, "--instance", "-i", help="Target instance profile ID"
    ),
    fake: bool = typer.Option(False, "--fake", help="Simulate Table API property updates"),
) -> None:
    """Apply demo bundle system properties to target ServiceNow instance."""
    bundle_path = settings.get_bundles_dir() / bundle_id
    if not bundle_path.exists():
        console.print(f"[bold red]Error:[/bold red] Demo bundle '{bundle_id}' not found.")
        raise typer.Exit(code=1)

    with db_session() as repo:
        inst = _get_target_instance(repo, instance)
    if not inst:
        console.print("[bold red]Error:[/bold red] Target instance not found.")
        raise typer.Exit(code=1)

    engine = PropertyEngine()
    res = asyncio.run(
        engine.apply_bundle_properties(
            bundle_id=bundle_id,
            bundle_path=bundle_path,
            instance=inst,
            fake_mode=fake,
        )
    )

    if res.success:
        console.print(
            Panel(
                f"[bold green]Applied {res.applied_count} properties to instance "
                f"'{inst.name}'[/bold green]\n" + "\n".join(f"  - {d}" for d in res.details),
                title="System Properties Applied",
            )
        )
    else:
        console.print(f"[bold red]Failed to apply properties:[/bold red] {res.details}")
        raise typer.Exit(code=1)


@properties_app.command("restore")
def restore_properties(
    bundle_id: str = typer.Argument(..., help="Demo bundle identifier"),
    instance: str | None = typer.Option(
        None, "--instance", "-i", help="Target instance profile ID"
    ),
    fake: bool = typer.Option(False, "--fake", help="Simulate Table API property restoration"),
) -> None:
    """Restore original system properties from snapshot."""
    with db_session() as repo:
        inst = _get_target_instance(repo, instance)
    if not inst:
        console.print("[bold red]Error:[/bold red] Target instance not found.")
        raise typer.Exit(code=1)

    engine = PropertyEngine()
    res = asyncio.run(
        engine.restore_properties(
            bundle_id=bundle_id,
            instance=inst,
            fake_mode=fake,
        )
    )

    if res.success:
        console.print(
            Panel(
                f"[bold green]Restored {res.restored_count} properties on instance "
                f"'{inst.name}'[/bold green]\n" + "\n".join(f"  - {d}" for d in res.details),
                title="System Properties Restored",
            )
        )
    else:
        console.print(f"[bold red]Failed to restore properties:[/bold red] {res.details}")
        raise typer.Exit(code=1)


def reset_demo_cmd(
    bundle_id: str = typer.Argument(..., help="Demo bundle identifier"),
    instance: str | None = typer.Option(
        None, "--instance", "-i", help="Target instance profile ID"
    ),
    fake: bool = typer.Option(False, "--fake", help="Simulate reset without live API calls"),
) -> None:
    """Unified demo teardown: rollback seed data and restore system properties."""
    bundle_path = settings.get_bundles_dir() / bundle_id
    if not bundle_path.exists():
        console.print(f"[bold red]Error:[/bold red] Demo bundle '{bundle_id}' not found.")
        raise typer.Exit(code=1)

    with db_session() as repo:
        inst = _get_target_instance(repo, instance)
        if not inst:
            console.print("[bold red]Error:[/bold red] Target instance not found.")
            raise typer.Exit(code=1)

        # 1. Rollback active seed records for this bundle and instance
        seed_engine = SeedEngine(repository=repo, fake_mode=fake)
        active_ops = [
            op
            for op in repo.list_seed_operations(limit=100)
            if op.bundle_id == bundle_id and op.status == "completed" and op.instance_id == inst.id
        ]
        seed_rolled_back = 0
        for op in active_ops:
            count, _ = asyncio.run(seed_engine.rollback(op.id))
            seed_rolled_back += count

    # 2. Restore properties
    prop_engine = PropertyEngine()
    prop_res = asyncio.run(
        prop_engine.restore_properties(
            bundle_id=bundle_id,
            instance=inst,
            fake_mode=fake,
        )
    )

    msg = (
        f"[bold green]Reset completed for demo '{bundle_id}' on instance '{inst.name}'"
        f"[/bold green]\n"
        f"  - Rolled back seed records: {seed_rolled_back}\n"
        f"  - Restored system properties: {prop_res.restored_count}"
    )
    console.print(Panel(msg, title="Demo Teardown & Reset"))
