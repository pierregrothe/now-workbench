"""CLI subcommands for inspecting and diffing ServiceNow Fluent SDK schemas."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from now_workbench.config.settings import settings
from now_workbench.fluent.engine import FluentEngine

fluent_app = typer.Typer(
    name="fluent",
    help="Inspect and diff ServiceNow Fluent SDK (*.now.ts) schemas",
)
console = Console()


@fluent_app.command("inspect")
def inspect_fluent(
    bundle_id: str = typer.Argument(..., help="Demo bundle identifier"),
) -> None:
    """Inspect Fluent SDK tables and columns defined in a demo bundle."""
    bundle_path = settings.get_bundles_dir() / bundle_id
    if not bundle_path.exists():
        console.print(f"[bold red]Error:[/bold red] Demo bundle '{bundle_id}' not found.")
        raise typer.Exit(code=1)

    engine = FluentEngine()
    tables = engine.load_bundle_schemas(bundle_path)
    if not tables:
        msg = f"[yellow]No Fluent schema (*.now.ts) tables found in '{bundle_id}'.[/yellow]"
        console.print(msg)
        return

    for tbl in tables:
        tbl_display = Table(title=f"Table: {tbl.name} ({tbl.label})", show_header=True)
        tbl_display.add_column("Column Name", style="cyan")
        tbl_display.add_column("Type", style="magenta")
        tbl_display.add_column("Reference", style="blue")
        tbl_display.add_column("Mandatory", style="yellow")
        tbl_display.add_column("Max Length", style="green")

        for col in tbl.columns:
            tbl_display.add_row(
                col.name,
                col.column_type,
                col.reference or "-",
                "Yes" if col.mandatory else "No",
                str(col.max_length) if col.max_length else "-",
            )

        console.print(tbl_display)


@fluent_app.command("diff")
def diff_fluent(
    bundle_a: str = typer.Argument(..., help="Base demo bundle identifier"),
    bundle_b: str = typer.Argument(..., help="Target demo bundle to compare against"),
) -> None:
    """Compare Fluent SDK schemas between two demo bundles."""
    bundles_dir = settings.get_bundles_dir()
    path_a = bundles_dir / bundle_a
    path_b = bundles_dir / bundle_b

    if not path_a.exists():
        console.print(f"[bold red]Error:[/bold red] Bundle '{bundle_a}' not found.")
        raise typer.Exit(code=1)
    if not path_b.exists():
        console.print(f"[bold red]Error:[/bold red] Bundle '{bundle_b}' not found.")
        raise typer.Exit(code=1)

    engine = FluentEngine()
    diff = engine.compute_diff(
        engine.load_bundle_schemas(path_a),
        engine.load_bundle_schemas(path_b),
    )

    if diff.identical:
        console.print(
            Panel(
                f"[bold green]Schemas in '{bundle_a}' and '{bundle_b}' are structurally "
                f"identical.[/bold green]",
                title="Fluent Schema Diff",
            )
        )
        return

    output_lines: list[str] = []
    if diff.added_tables:
        added_str = ", ".join(diff.added_tables)
        output_lines.append(f"[bold green]+ Added Tables:[/bold green] {added_str}")
    if diff.removed_tables:
        rem_str = ", ".join(diff.removed_tables)
        output_lines.append(f"[bold red]- Removed Tables:[/bold red] {rem_str}")
    if diff.modified_tables:
        output_lines.append("[bold yellow]~ Modified Tables:[/bold yellow]")
        for tbl_name, changes in diff.modified_tables.items():
            output_lines.append(f"  * {tbl_name}:")
            for ch in changes:
                output_lines.append(f"    - {ch}")

    console.print(Panel("\n".join(output_lines), title=f"Fluent Diff: {bundle_a} -> {bundle_b}"))
