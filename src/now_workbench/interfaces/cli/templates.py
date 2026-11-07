"""Template CLI commands for now-workbench."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from now_workbench.domains.templates import (
    TemplateEngine,
    TemplateInstantiationRequest,
    TemplateRepository,
)
from now_workbench.platform.config.settings import settings
from now_workbench.platform.db.session import db_session

console = Console()
template_app = typer.Typer(name="template", help="Manage reusable customer templates")


@template_app.command("list")
def list_templates_cmd() -> None:
    """List all available customization templates."""
    with db_session() as conn:
        templates = TemplateRepository(conn).list_templates()

    if not templates:
        console.print("[yellow]No customization templates registered.[/yellow]")
        return

    table = Table(title="Customization Templates", header_style="bold cyan")
    table.add_column("ID", style="bold white")
    table.add_column("Template Name")
    table.add_column("Base Bundle", style="magenta")
    table.add_column("Version", style="green")
    table.add_column("Description", style="dim")

    for tmpl in templates:
        table.add_row(
            tmpl.id,
            tmpl.name,
            tmpl.base_bundle_id,
            tmpl.version,
            tmpl.description[:60] + "..." if len(tmpl.description) > 60 else tmpl.description,
        )
    console.print(table)


@template_app.command("generate")
def generate_template_cmd(
    template_id: str = typer.Argument(..., help="Template ID to instantiate"),
    target_bundle_id: str = typer.Argument(..., help="New target bundle directory name"),
    customer_name: str = typer.Argument(..., help="Customer organization name"),
    primary_color: str = typer.Option(
        "#23a17e", "--primary-color", "-c", help="Brand primary color"
    ),
    secondary_color: str = typer.Option(
        "#0284c7", "--secondary-color", "-s", help="Secondary color"
    ),
    group: str = typer.Option(
        "IT Support Tier 1", "--group", "-g", help="Default assignment group"
    ),
    logo: str = typer.Option("", "--logo", "-l", help="Logo URL"),
) -> None:
    """Generate a customer-tailored customization bundle from a template."""
    with db_session() as conn:
        templates = {t.id: t for t in TemplateRepository(conn).list_templates()}

    if template_id not in templates:
        console.print(f"[red]Template '{template_id}' not found in registry.[/red]")
        raise typer.Exit(code=1)

    req = TemplateInstantiationRequest(
        target_bundle_id=target_bundle_id,
        customer_name=customer_name,
        primary_color=primary_color,
        secondary_color=secondary_color,
        logo_url=logo,
        assignment_group=group,
    )

    base_bundle_id = templates[template_id].base_bundle_id
    bundles_dir = settings.get_bundles_dir()
    engine = TemplateEngine(bundles_dir=bundles_dir, output_dir=bundles_dir)
    try:
        out_path = engine.instantiate(base_bundle_id, req)
        console.print(
            f"[green][OK][/green] Generated tailored bundle for [bold]{customer_name}[/bold]!"
        )
        console.print(f"  Location: [cyan]{out_path.resolve()}[/cyan]")
        console.print(f"  Primary Brand Color: [bold]{primary_color}[/bold]")
        console.print(f"  Assignment Group: [bold]{group}[/bold]")
    except Exception as exc:
        console.print(f"[red]Template instantiation failed: {exc}[/red]")
        raise typer.Exit(code=1)


@template_app.command("inspect")
def inspect_template_cmd(
    template_id: str = typer.Argument(..., help="Template ID to inspect"),
) -> None:
    """Inspect parameters schema and details for a customization template."""
    with db_session() as conn:
        templates = {t.id: t for t in TemplateRepository(conn).list_templates()}
    if template_id not in templates:
        console.print(f"[red]Template '{template_id}' not found.[/red]")
        raise typer.Exit(code=1)

    tmpl = templates[template_id]
    console.print(
        Panel(
            f"[bold cyan]{tmpl.name}[/bold cyan] ([green]v{tmpl.version}[/green])\n"
            f"[dim]{tmpl.description}[/dim]\n\n"
            f"- Base Bundle: {tmpl.base_bundle_id}\n"
            f"- Parameters: {', '.join(tmpl.parameters_schema.keys()) or 'None'}",
            title=f"Template: {template_id}",
            border_style="cyan",
        )
    )
