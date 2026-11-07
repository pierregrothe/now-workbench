# src/now_workbench/interfaces/cli/synthesizer.py
# CLI commands: synthesize a demo bundle; capture a screenshot or video of an instance.
# Author: Pierre Grothe
# Date: 2026-11-07
"""CLI commands for Use-Case Demo Synthesis and Playwright Instance Capture."""

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel

from now_workbench.domains.capture import (
    CaptureFailedError,
    CaptureRequest,
    PlaywrightCaptureEngine,
)
from now_workbench.domains.instances import InstanceRepository, is_simulated
from now_workbench.domains.settings import PreferencesRepository
from now_workbench.domains.synthesizer import (
    NoReleaseError,
    UseCaseSynthesisRequest,
    UseCaseSynthesizer,
    resolve_synthesis_release,
)
from now_workbench.interfaces.cli.ids import safe_id
from now_workbench.platform.config.settings import settings
from now_workbench.platform.db.session import db_session

__all__ = ["capture_demo_cmd", "synthesize_demo_cmd"]

console = Console()


def synthesize_demo_cmd(
    use_case: str = typer.Argument(..., help="Natural language description of the use case"),
    customer: str = typer.Option("Acme Global", "--customer", "-c", help="Customer name"),
    industry: str = typer.Option("Enterprise IT", "--industry", "-i", help="Industry vertical"),
    bundle_id: str | None = typer.Option(None, "--id", help="Explicit bundle slug"),
    release: str | None = typer.Option(
        None, "--release", "-r", help="ServiceNow release (default: detected from the instance)"
    ),
    color: str = typer.Option("#23a17e", "--color", help="Brand primary hex color"),
) -> None:
    """Synthesize a complete demo bundle (Fluent schema, seed data, properties, narrative)."""
    with db_session() as conn:
        try:
            target_release = resolve_synthesis_release(conn, release, None)
        except NoReleaseError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from exc
    synthesizer = UseCaseSynthesizer(bundles_dir=settings.get_bundles_dir())
    res = synthesizer.synthesize(
        UseCaseSynthesisRequest(
            use_case=use_case,
            customer_name=customer,
            industry=industry,
            bundle_id=bundle_id,
            sn_release=target_release,
            primary_color=color,
        )
    )
    msg = (
        f"[bold green]Synthesized Demo Bundle:[/bold green] [cyan]{res.bundle_id}[/cyan]\n"
        f"  - Customer: {res.customer_name} ({res.industry})\n"
        f"  - Fluent Table: {res.fluent_table_name}\n"
        f"  - Seed Records: {len(res.seed_records)}\n"
        f"  - Location: {res.bundle_path}"
    )
    console.print(Panel(msg, title="Use-Case Demo Synthesizer"))


def capture_demo_cmd(
    bundle_id: str = typer.Argument(
        "sample-ai-assistant", callback=safe_id, help="Demo bundle identifier"
    ),
    target_path: str = typer.Option(
        "/now/nav/ui/classic/params/target/incident_list.do",
        "--path",
        "-p",
        help="ServiceNow URI path to capture",
    ),
    media_type: str = typer.Option("screenshot", "--type", "-t", help="screenshot or video"),
    label: str = typer.Option("Instance Capture", "--label", "-l", help="Capture caption"),
    instance: str | None = typer.Option(None, "--instance", help="Target instance ID"),
    fake: bool = typer.Option(False, "--fake", help="Simulate capture offline"),
) -> None:
    """Capture a Playwright screenshot (.png) or video (.webm) of the target instance."""
    with db_session() as conn:
        inst = InstanceRepository(conn).resolve(instance)
        wait_ms = PreferencesRepository(conn).get_workbench_preferences().capture_wait_timeout_ms
    if inst is None:
        target = (
            f"Instance '{instance}' not found" if instance else "No default instance registered"
        )
        console.print(f"[bold red]Error:[/bold red] {target}. Register an instance first.")
        raise typer.Exit(code=1)

    engine = PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir())
    try:
        artifact = asyncio.run(
            engine.capture(
                CaptureRequest(
                    bundle_id=bundle_id,
                    instance_id=instance,
                    target_path=target_path,
                    media_type=media_type,
                    label=label,
                    fake_mode=is_simulated(inst, fake),
                ),
                instance_url=inst.url,
                username=inst.username,
                password=inst.password,
                release=inst.release,
                wait_timeout_ms=wait_ms,
            )
        )
    except CaptureFailedError as exc:
        console.print(f"[bold red]Capture failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc
    msg = (
        f"[bold green]Captured {artifact.media_type}:[/bold green] {artifact.filename}\n"
        f"  - Instance: {artifact.instance_url}{artifact.target_path}\n"
        f"  - Engine: {artifact.engine}\n"
        f"  - File: {artifact.file_path}"
    )
    console.print(Panel(msg, title="Playwright Media Capture"))
