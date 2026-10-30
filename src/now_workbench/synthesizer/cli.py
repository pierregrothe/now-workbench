"""CLI commands for Use-Case Demo Synthesis and Playwright Instance Capture."""

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel

from now_workbench.capture.engine import PlaywrightCaptureEngine
from now_workbench.capture.models import CaptureRequest
from now_workbench.config.settings import settings
from now_workbench.db.session import db_session
from now_workbench.synthesizer.engine import UseCaseSynthesizer
from now_workbench.synthesizer.models import UseCaseSynthesisRequest

console = Console()


def synthesize_demo_cmd(
    use_case: str = typer.Argument(..., help="Natural language description of the use case"),
    customer: str = typer.Option("Acme Global", "--customer", "-c", help="Customer name"),
    industry: str = typer.Option("Enterprise IT", "--industry", "-i", help="Industry vertical"),
    bundle_id: str | None = typer.Option(None, "--id", help="Explicit bundle slug"),
    release: str = typer.Option("Zurich", "--release", "-r", help="ServiceNow release"),
    color: str = typer.Option("#23a17e", "--color", help="Brand primary hex color"),
) -> None:
    """Synthesize a complete demo bundle (Fluent schema, seed data, properties, narrative)."""
    synthesizer = UseCaseSynthesizer(bundles_dir=settings.get_bundles_dir())
    res = synthesizer.synthesize(
        UseCaseSynthesisRequest(
            use_case=use_case,
            customer_name=customer,
            industry=industry,
            bundle_id=bundle_id,
            sn_release=release,
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
    bundle_id: str = typer.Argument("sample-ai-assistant", help="Demo bundle identifier"),
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
    with db_session() as repo:
        inst = repo.get_instance(instance) if instance else repo.get_default_instance()
    inst_url = inst.url if inst else "https://demoalectriallwfau164179.service-now.com"

    engine = PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir())
    artifact = asyncio.run(
        engine.capture(
            CaptureRequest(
                bundle_id=bundle_id,
                instance_id=instance,
                target_path=target_path,
                media_type=media_type,
                label=label,
                fake_mode=fake,
            ),
            instance_url=inst_url,
        )
    )
    msg = (
        f"[bold green]Captured {artifact.media_type}:[/bold green] {artifact.filename}\n"
        f"  - Instance: {artifact.instance_url}{artifact.target_path}\n"
        f"  - Engine: {artifact.engine}\n"
        f"  - File: {artifact.file_path}"
    )
    console.print(Panel(msg, title="Playwright Media Capture"))
