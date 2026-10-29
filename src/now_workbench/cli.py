"""CLI entrypoint for now-workbench."""

import asyncio
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from now_workbench import __version__
from now_workbench.bundles.manager import BundleManager
from now_workbench.config.settings import settings
from now_workbench.sdk.runner import NowSdkRunner

app = typer.Typer(
    name="workbench",
    help="AI-native developer & demonstration workbench for the ServiceNow SDK",
    add_completion=False,
)
demo_app = typer.Typer(name="demo", help="Manage demonstration packages")
app.add_typer(demo_app)

console = Console()


@app.command()
def version() -> None:
    """Print the workbench version."""
    console.print(f"[bold cyan]now-workbench[/bold cyan] version [green]{__version__}[/green]")


@app.command()
def doctor() -> None:
    """Run diagnostics on local toolchain, ServiceNow SDK, and environment."""
    console.print(
        Panel(
            "[bold white]now-workbench Diagnostic Health Check[/bold white]",
            border_style="cyan",
        )
    )

    runner = NowSdkRunner(now_sdk_bin=settings.now_sdk_bin, node_bin=settings.node_bin)
    probe = runner.probe_environment()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_column("Details")

    # Node.js
    if probe["node_available"]:
        table.add_row("Node.js", "[green]✓ Available[/green]", str(probe["node_path"]))
    else:
        table.add_row(
            "Node.js", "[red]✗ Missing[/red]", "Install Node.js 20+ LTS to run @servicenow/sdk"
        )

    # now-sdk
    if probe["now_sdk_available"]:
        table.add_row("ServiceNow SDK", "[green]✓ Available[/green]", str(probe["now_sdk_path"]))
    else:
        table.add_row(
            "ServiceNow SDK",
            "[yellow]! Not in PATH[/yellow]",
            "Run: npm install -g @servicenow/sdk",
        )

    # Instance
    if settings.sn_instance_url:
        table.add_row("Target Instance", "[green]✓ Configured[/green]", settings.sn_instance_url)
    else:
        table.add_row(
            "Target Instance",
            "[yellow]! Unset[/yellow]",
            "Set WORKBENCH_SN_INSTANCE_URL or configure in UI",
        )

    # Claude API / Otto
    if settings.anthropic_api_key:
        table.add_row("Otto (Claude API)", "[green]✓ Connected[/green]", settings.claude_model)
    else:
        table.add_row(
            "Otto (Claude API)",
            "[yellow]! Simulation[/yellow]",
            "Set WORKBENCH_ANTHROPIC_API_KEY for live Claude streaming",
        )

    console.print(table)


@demo_app.command("list")
def list_demos() -> None:
    """List installed demonstration packages."""
    mgr = BundleManager(storage_dir=settings.bundles_dir)
    bundles = mgr.list_bundles()

    if not bundles:
        console.print("[yellow]No demonstration bundles found in storage.[/yellow]")
        console.print(f"Bundles directory: [dim]{settings.bundles_dir}[/dim]")
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
    mgr = BundleManager(storage_dir=settings.bundles_dir)
    bundle_path = settings.bundles_dir / bundle_id
    if not bundle_path.exists():
        console.print(f"[red]Error: Bundle '{bundle_id}' not found.[/red]")
        raise typer.Exit(code=1)

    info = mgr.inspect_bundle(bundle_path)
    console.print(
        Panel(
            f"[bold cyan]{info.manifest.name}[/bold cyan] ([green]v{info.manifest.version}[/green])\n"
            f"[dim]{info.manifest.description}[/dim]\n\n"
            f"• Target Release: {info.manifest.sn_release}\n"
            f"• Required Plugins: {', '.join(info.manifest.required_plugins) or 'None'}\n"
            f"• Fluent Files: {len(info.fluent_files)}\n"
            f"• Seed Files: {len(info.seed_files)}\n"
            f"• Walkthrough Script: {'Available' if info.has_walkthrough else 'None'}",
            title=f"Demo: {bundle_id}",
            border_style="cyan",
        )
    )


@demo_app.command("export")
def export_demo(bundle_id: str, output: Path = Path("demo.sn-demo.zip")) -> None:
    """Export a demonstration package as a portable .sn-demo.zip archive."""
    mgr = BundleManager(storage_dir=settings.bundles_dir)
    try:
        archive = mgr.export_bundle(bundle_id, output)
        console.print(f"[green]✓ Exported bundle to:[/green] {archive.resolve()}")
    except Exception as e:
        console.print(f"[red]Failed to export bundle: {e}[/red]")
        raise typer.Exit(code=1)


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
