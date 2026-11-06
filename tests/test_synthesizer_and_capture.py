"""Tests for UseCaseSynthesizer, PlaywrightCaptureEngine, CLI, and FastAPI routes."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from now_workbench.api.app import create_app
from now_workbench.capture.engine import PlaywrightCaptureEngine
from now_workbench.capture.models import CaptureRequest
from now_workbench.cli import app as cli_app
from now_workbench.config.settings import settings
from now_workbench.db import InstanceCreate, InstanceProfile, db_session
from now_workbench.synthesizer.engine import (
    UseCaseSynthesizer,
    _extract_persona_parts,
    _slugify,
)
from now_workbench.synthesizer.models import UseCaseSynthesisRequest


def test_slugify_and_persona_helpers() -> None:
    """Verify _slugify and _extract_persona_parts edge cases."""
    assert _slugify("!!!") == "custom-demo"
    assert _slugify("Acme Financial Triage") == "acme-financial-triage"

    name1, role1 = _extract_persona_parts("Amelia Chen (Clinical Lead)", "Fallback")
    assert name1 == "Amelia Chen"
    assert role1 == "Clinical Lead"

    name2, role2 = _extract_persona_parts("Marcus Vance", "Solution Stakeholder")
    assert name2 == "Marcus Vance"
    assert role2 == "Solution Stakeholder"


def test_use_case_synthesizer_creates_bundle_artifacts(tmp_path: Path) -> None:
    """Verify UseCaseSynthesizer generates Fluent .now.ts, seed JSON, and SC narrative."""
    synthesizer = UseCaseSynthesizer(bundles_dir=tmp_path)
    req = UseCaseSynthesisRequest(
        use_case=(
            "Automate clinical device triage and field technician dispatch "
            "for hospital infusion pumps."
        ),
        customer_name="Novartis Health",
        industry="Healthcare",
        sn_release="Zurich",
        persona_primary="Amelia Chen (Clinical Lead)",
        persona_secondary="Marcus Vance",
        primary_color="#62d84e",
    )
    result = synthesizer.synthesize(req)

    assert result.bundle_id.startswith("novartis-health-")
    bundle_dir = Path(result.bundle_path)
    assert (bundle_dir / "manifest.json").exists()
    assert (bundle_dir / "fluent" / f"{result.bundle_id}.now.ts").exists()
    assert (bundle_dir / "seed" / "01_synthesized_records.json").exists()
    assert (bundle_dir / "properties" / "sys_properties.json").exists()
    assert (bundle_dir / "walkthrough" / "guide.md").exists()
    assert "Table({" in result.fluent_code
    assert len(result.seed_records) == 3
    assert "## Walkthrough Stages" in result.narrative_markdown


async def test_playwright_capture_engine_fake_screenshot_and_video(tmp_path: Path) -> None:
    """Verify PlaywrightCaptureEngine in fake_mode generates valid PNG and WebM artifacts."""
    engine = PlaywrightCaptureEngine(bundles_dir=tmp_path)

    # Initially empty before captures.json exists
    assert engine.list_captures("demo-bundle") == []

    shot_req = CaptureRequest(
        bundle_id="demo-bundle",
        target_path="now/workspace/agent",
        media_type="screenshot",
        label="Agent Workspace Overview",
        fake_mode=True,
    )
    shot_artifact = await engine.capture(shot_req, instance_url="https://dev12345.service-now.com/")
    assert shot_artifact.media_type == "screenshot"
    assert shot_artifact.engine == "playwright-simulated"
    assert shot_artifact.instance_url == "https://dev12345.service-now.com"
    assert shot_artifact.target_path == "/now/workspace/agent"
    assert Path(shot_artifact.file_path).exists()

    vid_req = CaptureRequest(
        bundle_id="demo-bundle",
        target_path="/incident_list.do",
        media_type="video",
        label="ServiceNow Video Capture",
        fake_mode=True,
    )
    vid_artifact = await engine.capture(vid_req, instance_url="https://dev12345.service-now.com")
    assert vid_artifact.media_type == "video"
    assert vid_artifact.filename.endswith(".webm")

    listed = engine.list_captures("demo-bundle")
    assert len(listed) == 2
    modes = {item.media_type for item in listed}
    assert modes == {"screenshot", "video"}

    # Update capture label
    updated = engine.update_capture(
        "demo-bundle",
        shot_artifact.filename,
        label="Updated Workspace View",
    )
    assert updated.label == "Updated Workspace View"

    # Delete video capture
    del_ok = engine.delete_capture("demo-bundle", vid_artifact.filename)
    assert del_ok is True
    remaining = engine.list_captures("demo-bundle")
    assert len(remaining) == 1
    assert remaining[0].filename == shot_artifact.filename
    assert not Path(vid_artifact.file_path).exists()


async def test_playwright_capture_engine_live_cli_execution(tmp_path: Path) -> None:
    """Verify PlaywrightCaptureEngine(fake_mode=False) invokes npx playwright screenshot."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    npx_script = bin_dir / "npx"
    npx_script.write_text(
        "#!/bin/sh\nfor last; do true; done\nprintf '\\211PNG\\r\\n\\032\\n' > \"$last\"\nexit 0\n",
        encoding="utf-8",
    )
    npx_script.chmod(npx_script.stat().st_mode | stat.S_IEXEC)

    old_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{bin_dir}:{old_path}"
    try:
        engine = PlaywrightCaptureEngine(bundles_dir=tmp_path / "bundles")
        req = CaptureRequest(
            bundle_id="live-bundle",
            target_path="/incident_list.do",
            media_type="screenshot",
            fake_mode=False,
        )
        artifact = await engine.capture(req, instance_url="https://dev99999.service-now.com")
        assert artifact.engine in ("google-chrome-native", "playwright-chromium")

        # Video mode in live engine uses deterministic fallback container
        vid_req = CaptureRequest(
            bundle_id="live-bundle",
            target_path="/incident_list.do",
            media_type="video",
            fake_mode=False,
        )
        vid_artifact = await engine.capture(
            vid_req, instance_url="https://dev99999.service-now.com"
        )
        assert vid_artifact.engine in ("google-chrome-native", "playwright-simulated")
    finally:
        os.environ["PATH"] = old_path


async def test_playwright_capture_engine_missing_npx(tmp_path: Path) -> None:
    """Verify _run_playwright_cli returns False cleanly when npx is not on PATH."""
    old_path = os.environ.get("PATH", "")
    os.environ["PATH"] = str(tmp_path / "empty-bin")
    try:
        engine = PlaywrightCaptureEngine(bundles_dir=tmp_path / "bundles")
        req = CaptureRequest(
            bundle_id="fallback-bundle",
            target_path="/incident_list.do",
            media_type="screenshot",
            fake_mode=False,
        )
        artifact = await engine.capture(req, instance_url="https://dev99999.service-now.com")
        assert artifact.engine == "playwright-simulated"
    finally:
        os.environ["PATH"] = old_path


def test_api_synthesize_and_captures_routes(tmp_path: Path) -> None:
    """Verify FastAPI /api/demos/synthesize and /api/demos/{id}/captures endpoints."""
    old_bundles = settings.bundles_dir
    object.__setattr__(settings, "bundles_dir", tmp_path)
    try:
        app = create_app()
        client = TestClient(app)

        synth_res = client.post(
            "/api/demos/synthesize",
            json={
                "use_case": "Proactive IT hardware asset refresh and incident correlation.",
                "customer_name": "Siemens Energy",
                "industry": "Manufacturing",
                "sn_release": "Zurich",
                "persona_primary": "Elena Rostova (IT Asset Manager)",
                "primary_color": "#62d84e",
            },
        )
        assert synth_res.status_code == 200
        synth_data = synth_res.json()
        bundle_id = synth_data["bundle_id"]
        assert synth_data["fluent_table_name"].startswith("x_snc_")

        # Capture a screenshot via API (with default instance lookup)
        cap_res = client.post(
            f"/api/demos/{bundle_id}/captures",
            json={
                "bundle_id": bundle_id,
                "target_path": "/now/nav/ui/classic",
                "media_type": "screenshot",
                "label": "Classic UI View",
                "fake_mode": True,
            },
        )
        assert cap_res.status_code == 200
        cap_data = cap_res.json()
        file_name = cap_data["filename"]

        # List captures
        list_res = client.get(f"/api/demos/{bundle_id}/captures")
        assert list_res.status_code == 200
        assert len(list_res.json()) == 1

        # Download capture file (.png)
        file_res = client.get(f"/api/demos/{bundle_id}/captures/{file_name}")
        assert file_res.status_code == 200
        assert file_res.headers["content-type"] == "image/png"

        # Capture a video (.webm) with an explicit, registered instance_id and download it
        vid_res = client.post(
            f"/api/demos/{bundle_id}/captures",
            json={
                "bundle_id": bundle_id,
                "instance_id": "default-instance",
                "target_path": "/now/nav/ui/classic",
                "media_type": "video",
                "label": "Walkthrough Recording",
                "fake_mode": True,
            },
        )
        assert vid_res.status_code == 200
        vid_file = vid_res.json()["filename"]
        vid_dl = client.get(f"/api/demos/{bundle_id}/captures/{vid_file}")
        assert vid_dl.status_code == 200
        assert vid_dl.headers["content-type"] == "video/webm"

        # 404 for missing capture file
        missing_res = client.get(f"/api/demos/{bundle_id}/captures/nonexistent.png")
        assert missing_res.status_code == 404

        # HTTP PATCH capture metadata
        patch_cap_res = client.request(
            "PATCH",
            f"/api/demos/{bundle_id}/captures/{file_name}",
            json={"label": "Renamed Screenshot"},
        )
        assert patch_cap_res.status_code == 200
        assert patch_cap_res.json()["label"] == "Renamed Screenshot"

        # DELETE capture
        del_cap_res = client.delete(f"/api/demos/{bundle_id}/captures/{file_name}")
        assert del_cap_res.status_code == 200
        remaining_caps = client.get(f"/api/demos/{bundle_id}/captures").json()
        assert len(remaining_caps) == 1

        # DELETE all captures for bundle
        clear_all_res = client.delete(f"/api/demos/{bundle_id}/captures")
        assert clear_all_res.status_code == 200
        assert clear_all_res.json()["deleted_count"] >= 1
        assert client.get(f"/api/demos/{bundle_id}/captures").json() == []

        # HTTP PATCH bundle manifest
        patch_b_res = client.request(
            "PATCH",
            f"/api/demos/{bundle_id}",
            json={"name": "API Renamed Bundle", "tags": ["custom", "api"]},
        )
        assert patch_b_res.status_code == 200
        assert patch_b_res.json()["manifest"]["name"] == "API Renamed Bundle"
        assert patch_b_res.json()["manifest"]["tags"] == ["custom", "api"]

        # DELETE bundle
        del_b_res = client.delete(f"/api/demos/{bundle_id}")
        assert del_b_res.status_code == 200
    finally:
        object.__setattr__(settings, "bundles_dir", old_bundles)


def test_cli_demo_synthesize_and_capture(tmp_path: Path) -> None:
    """Verify CLI commands `workbench demo synthesize` and `workbench demo capture`."""
    old_bundles = settings.bundles_dir
    object.__setattr__(settings, "bundles_dir", tmp_path)
    try:
        runner = CliRunner()
        no_instance = runner.invoke(cli_app, ["demo", "synthesize", "Incident triage."])
        assert no_instance.exit_code == 1
        assert "register an instance" in no_instance.stdout

        with db_session() as repo:
            repo.add_instance(
                InstanceCreate(
                    id="cli-inst", name="CLI", url="https://cli.service-now.com", is_default=True
                )
            )
            repo.save_instance_profile(InstanceProfile(instance_id="cli-inst", release="Australia"))
        synth_result = runner.invoke(
            cli_app,
            [
                "demo",
                "synthesize",
                "Automated security incident response and SOAR enrichment.",
                "--customer",
                "CrowdGuard",
                "--industry",
                "Cybersecurity",
            ],
        )
        assert synth_result.exit_code == 0
        assert "Synthesized Demo Bundle:" in synth_result.stdout

        # Extract generated bundle_id from stdout
        synth_line = [
            line for line in synth_result.stdout.splitlines() if "Synthesized Demo Bundle:" in line
        ][0]
        synth_id = synth_line.split("Synthesized Demo Bundle:")[1].split()[0].strip()

        cap_result = runner.invoke(
            cli_app,
            [
                "demo",
                "capture",
                synth_id,
                "--path",
                "/incident_list.do",
                "--type",
                "screenshot",
                "--fake",
            ],
        )
        assert cap_result.exit_code == 0
        assert "Captured screenshot:" in cap_result.stdout

        # List captures
        list_res = runner.invoke(cli_app, ["demo", "list-captures", synth_id])
        assert list_res.exit_code == 0
        assert f"Media Captures: {synth_id}" in list_res.stdout

        # Extract filename from cap_result
        cap_line = [
            line for line in cap_result.stdout.splitlines() if "Captured screenshot:" in line
        ][0]
        captured_file = cap_line.split("Captured screenshot:")[1].split()[0].strip()

        # Update capture
        up_cap_res = runner.invoke(
            cli_app,
            [
                "demo",
                "update-capture",
                synth_id,
                captured_file,
                "--label",
                "Updated CLI Label",
            ],
        )
        assert up_cap_res.exit_code == 0
        assert "Updated capture" in up_cap_res.stdout

        # Delete capture
        del_cap_res = runner.invoke(
            cli_app,
            ["demo", "delete-capture", synth_id, captured_file],
        )
        assert del_cap_res.exit_code == 0
        assert "Deleted capture artifact" in del_cap_res.stdout

        # Capture another file and test --all deletion
        engine = PlaywrightCaptureEngine(bundles_dir=tmp_path)
        runner.invoke(
            cli_app,
            ["demo", "capture", synth_id, "--fake", "--type", "video"],
        )
        assert len(engine.list_captures(synth_id)) == 1

        del_all_res = runner.invoke(
            cli_app,
            ["demo", "delete-capture", synth_id, "--all"],
        )
        assert del_all_res.exit_code == 0
        assert "Cleared all" in del_all_res.stdout
        assert len(engine.list_captures(synth_id)) == 0

        # Update demo bundle
        up_demo_res = runner.invoke(
            cli_app,
            [
                "demo",
                "update",
                synth_id,
                "--name",
                "New Assistant Name",
                "--tags",
                "ai,now",
            ],
        )
        assert up_demo_res.exit_code == 0
        assert "Updated demo bundle" in up_demo_res.stdout

        # Delete demo bundle
        del_demo_res = runner.invoke(
            cli_app,
            ["demo", "delete", synth_id, "--force"],
        )
        assert del_demo_res.exit_code == 0
        assert f"Demonstration bundle '{synth_id}' deleted." in del_demo_res.stdout
    finally:
        object.__setattr__(settings, "bundles_dir", old_bundles)


def test_workbench_settings_api_and_cli(tmp_path: Path) -> None:
    """Verify encrypted SQLite storage, masked /api/settings responses, and CLI config."""

    old_data = os.environ.get("WORKBENCH_DATA_DIR")
    os.environ["WORKBENCH_DATA_DIR"] = str(tmp_path)
    try:
        _run_workbench_settings_assertions()
    finally:
        if old_data is None:
            os.environ.pop("WORKBENCH_DATA_DIR", None)
        else:
            os.environ["WORKBENCH_DATA_DIR"] = old_data


def _run_workbench_settings_assertions() -> None:
    from now_workbench.db.session import db_session

    app = create_app()
    client = TestClient(app)

    # 1. GET initial settings
    get_res = client.get("/api/settings")
    assert get_res.status_code == 200
    initial = get_res.json()
    assert initial["claude_model"] == "claude-sonnet-5-5"
    assert "anthropic_api_key" not in initial

    # 2. PUT updated settings including Claude AI API Key and Media Capture defaults
    raw_secret = "sk-ant-test-livekey9876"
    put_res = client.put(
        "/api/settings",
        json={
            "anthropic_api_key": raw_secret,
            "claude_model": "claude-opus-4-5",
            "capture_viewport_width": 1920,
            "capture_viewport_height": 1080,
            "capture_wait_timeout_ms": 2500,
            "sc_author_name": "Pierre Grothe",
            "default_scoped_prefix": "x_acme",
        },
    )
    assert put_res.status_code == 200
    updated = put_res.json()
    assert "anthropic_api_key" not in updated
    assert updated["has_anthropic_api_key"] is True
    assert updated["anthropic_api_key_masked"] == "sk-ant-...9876"
    assert updated["claude_model"] == "claude-opus-4-5"
    assert updated["capture_viewport_width"] == 1920
    assert updated["sc_author_name"] == "Pierre Grothe"

    # Verify the raw SQLite payload is encrypted at rest and never contains the raw secret
    with db_session() as repo:
        payload = repo.conn.execute(
            "SELECT payload FROM user_preferences WHERE email = 'local@localhost';"
        ).fetchone()["payload"]
        sealed = repo.conn.execute(
            "SELECT sealed FROM secrets WHERE name = 'anthropic_api_key';"
        ).fetchone()["sealed"]
        assert raw_secret not in payload
        assert raw_secret.encode() not in sealed
        assert repo.get_decrypted_anthropic_api_key() == raw_secret

    # Verify echoing a masked string does not overwrite the encrypted key
    echo_res = client.put("/api/settings", json={"anthropic_api_key": "sk-ant-...9876"})
    assert echo_res.status_code == 200
    assert echo_res.json()["anthropic_api_key_masked"] == "sk-ant-...9876"

    # 3. POST reset settings
    reset_res = client.post("/api/settings/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["capture_viewport_width"] == 1440
    # Settings are per user; the shared Claude key survives a reset (ADR-018).
    assert reset_res.json()["has_anthropic_api_key"] is True
    assert client.delete("/api/settings/api-key").status_code == 200

    # 4. CLI: `workbench config show`, `workbench config set`, `workbench config reset`
    runner = CliRunner()
    show_res = runner.invoke(cli_app, ["config", "show"])
    assert show_res.exit_code == 0
    assert "Now Workbench Settings" in show_res.stdout

    set_res = runner.invoke(
        cli_app,
        [
            "config",
            "set",
            "--anthropic-api-key",
            "sk-ant-api03-cli9999",
            "--claude-model",
            "claude-haiku-4-5",
            "--viewport-width",
            "1280",
            "--viewport-height",
            "720",
        ],
    )
    assert set_res.exit_code == 0
    assert "sk-ant-...9999" in set_res.stdout

    # Show again when key is configured
    show_configured = runner.invoke(cli_app, ["config", "show"])
    assert show_configured.exit_code == 0
    assert "sk-ant-...9999" in show_configured.stdout

    cli_reset = runner.invoke(cli_app, ["config", "reset"])
    assert cli_reset.exit_code == 0
    assert "Reset Now Workbench settings" in cli_reset.stdout
