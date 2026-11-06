"""CLI subcommands for managing Now Workbench settings and preferences."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from now_workbench.db.models import WorkbenchPreferences, WorkbenchPreferencesUpdate
from now_workbench.db.session import db_session

config_app = typer.Typer(name="config", help="Manage Now Workbench settings and preferences")
console = Console()


def _format_masked_key(prefs: WorkbenchPreferences) -> str:
    """Format the masked Claude AI API key for CLI display."""
    if not prefs.has_anthropic_api_key:
        return "[yellow]Not configured (Simulation mode)[/yellow]"
    return f"[green]{prefs.anthropic_api_key_masked} (Encrypted)[/green]"


@config_app.command("show")
def show_config_cmd() -> None:
    """Display persisted Now Workbench settings and preferences."""
    with db_session() as repo:
        prefs = repo.get_workbench_preferences()

    table = Table(title="Now Workbench Settings", header_style="bold cyan")
    table.add_column("Category", style="magenta")
    table.add_column("Setting", style="bold white")
    table.add_column("Value", style="cyan")

    table.add_row("Claude AI & Intent", "Claude AI API Key", _format_masked_key(prefs))
    table.add_row("Claude AI & Intent", "Claude Model", prefs.claude_model)
    table.add_row("Claude AI & Intent", "Auto-Route Menu on Intent", str(prefs.auto_route_intent))
    table.add_row("Claude AI & Intent", "Auto-Execute on Route", str(prefs.auto_execute_intent))

    vp = f"{prefs.capture_viewport_width}x{prefs.capture_viewport_height}"
    table.add_row("Media Capture", "Default Viewport", vp)
    table.add_row("Media Capture", "Default Format", prefs.capture_default_media_type)
    table.add_row("Media Capture", "Wait Timeout (ms)", str(prefs.capture_wait_timeout_ms))
    table.add_row("Media Capture", "Offline Simulation", str(prefs.capture_fake_mode))

    table.add_row("SC Demo Synthesis", "SC Author Name", prefs.sc_author_name)
    table.add_row("SC Demo Synthesis", "Scoped Prefix", prefs.default_scoped_prefix)
    table.add_row("SC Demo Synthesis", "Brand Accent Color", prefs.default_brand_color)
    table.add_row("SC Demo Synthesis", "Narrative Tone", prefs.narrative_tone)

    table.add_row("UI & Toolchain", "Show Welcome on Startup", str(prefs.show_welcome_on_startup))
    table.add_row("UI & Toolchain", "SDK Simulation Mode", str(prefs.sdk_fake_mode))
    table.add_row("UI & Toolchain", "HUD Font Scale", prefs.hud_font_scale)

    console.print(table)


@config_app.command("set")
def set_config_cmd(
    api_key: str | None = typer.Option(
        None, "--anthropic-api-key", "-k", help="Claude AI API Key (encrypted at rest)"
    ),
    claude_model: str | None = typer.Option(None, "--claude-model", "-m", help="Claude AI model"),
    auto_route: bool | None = typer.Option(
        None, "--auto-route/--no-auto-route", help="Auto-switch menu on AI intent"
    ),
    viewport_width: int | None = typer.Option(
        None, "--viewport-width", help="Capture viewport width"
    ),
    viewport_height: int | None = typer.Option(
        None, "--viewport-height", help="Capture viewport height"
    ),
    media_type: str | None = typer.Option(
        None, "--media-type", help="Default capture format: screenshot or video"
    ),
    wait_timeout: int | None = typer.Option(
        None, "--wait-timeout", help="Capture page settle wait in ms"
    ),
    playwright_fake: bool | None = typer.Option(
        None, "--offline-capture/--no-offline-capture", help="Offline capture simulation"
    ),
    author_name: str | None = typer.Option(None, "--author-name", help="Default SC author name"),
    brand_color: str | None = typer.Option(None, "--brand-color", help="Default brand hex color"),
    welcome: bool | None = typer.Option(
        None, "--welcome/--no-welcome", help="Show Welcome modal on startup"
    ),
) -> None:
    """Update one or more Now Workbench settings in encrypted storage."""
    update = WorkbenchPreferencesUpdate(
        anthropic_api_key=api_key,
        claude_model=claude_model,
        auto_route_intent=auto_route,
        capture_viewport_width=viewport_width,
        capture_viewport_height=viewport_height,
        capture_default_media_type=media_type,
        capture_wait_timeout_ms=wait_timeout,
        capture_fake_mode=playwright_fake,
        sc_author_name=author_name,
        default_brand_color=brand_color,
        show_welcome_on_startup=welcome,
    )
    with db_session() as repo:
        updated = repo.update_workbench_preferences(update)
    console.print(
        Panel(
            f"[green][OK] Updated Now Workbench Settings[/green]\n"
            f"  - Claude Model: {updated.claude_model}\n"
            f"  - Claude API Key: {_format_masked_key(updated)}\n"
            f"  - Capture Viewport: "
            f"{updated.capture_viewport_width}x{updated.capture_viewport_height}",
            title="Workbench Config",
        )
    )


@config_app.command("reset")
def reset_config_cmd() -> None:
    """Reset Now Workbench settings back to factory defaults."""
    with db_session() as repo:
        repo.reset_workbench_preferences()
    console.print("[green][OK] Reset Now Workbench settings to defaults.[/green]")
