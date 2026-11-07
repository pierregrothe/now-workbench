"""Tests for end-to-end demonstration pipeline: evaluation, module installation,
properties, seeding, test execution, and video proof capture.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from now_workbench.ai.tools import execute_tool
from now_workbench.ai.tools.base import ToolContext
from now_workbench.bundles.pipeline import DemoPipelineEngine
from now_workbench.cli import app
from now_workbench.db import InstanceCreate, InstanceProfile, db_session
from now_workbench.db.repos.instances import InstanceRepository
from now_workbench.synthesizer.engine import UseCaseSynthesizer
from now_workbench.synthesizer.models import UseCaseSynthesisRequest


@pytest.fixture
def synthesized_demo(tmp_path: Path):
    """Synthesize a complete realistic demo bundle in an isolated directory."""
    bundles_dir = tmp_path / "bundles"
    bundles_dir.mkdir(parents=True, exist_ok=True)
    synthesizer = UseCaseSynthesizer(bundles_dir=bundles_dir)
    req = UseCaseSynthesisRequest(
        use_case="Automated incident triage and root cause isolation using Now Assist AI",
        customer_name="Novartis BioHealth",
        industry="Healthcare",
        sn_release="Zurich",
        primary_color="#0066cc",
    )
    result = synthesizer.synthesize(req)
    return bundles_dir, result.bundle_id


def test_evaluate_and_install_modules(tmp_path: Path, synthesized_demo):
    """Test evaluation of prerequisites and installation of required ServiceNow modules."""
    bundles_dir, bundle_id = synthesized_demo
    db_file = tmp_path / "test.db"

    with db_session(db_file) as conn:
        instance_repo = InstanceRepository(conn)
        inst = instance_repo.add_instance(
            InstanceCreate(
                id="inst-test-01",
                name="Test Dev Instance",
                url="https://testdev.service-now.com",
                is_default=True,
            )
        )
        # The release is detected at connection (ADR-014); simulate a detected profile.
        instance_repo.save_instance_profile(
            InstanceProfile(instance_id="inst-test-01", release="Zurich")
        )
        inst = instance_repo.get_instance("inst-test-01")
        assert inst is not None

        engine = DemoPipelineEngine(bundles_dir=bundles_dir, conn=conn)

        # 1. Initial evaluation should detect missing required plugins
        eval_before = engine.evaluate_bundle(bundle_id, inst, fake_mode=True)
        assert len(eval_before.required_plugins) >= 2
        assert "com.now_assist_core" in eval_before.required_plugins
        assert "com.snc.incident" in eval_before.required_plugins
        assert len(eval_before.missing_plugins) >= 2
        assert not eval_before.is_ready

        # 2. Install required modules
        installed = engine.install_required_modules(bundle_id, inst, fake_mode=True)
        assert len(installed) >= 2

        # 3. Post-install evaluation should show all satisfied and ready
        eval_after = engine.evaluate_bundle(bundle_id, inst, fake_mode=True)
        assert len(eval_after.missing_plugins) == 0
        assert eval_after.is_ready
        assert eval_after.system_properties_count > 0
        assert eval_after.seed_records_count > 0
        assert eval_after.walkthrough_stages_count > 0


@pytest.mark.asyncio
async def test_full_demo_pipeline_with_video_proof(tmp_path: Path, synthesized_demo):
    """Test full demo pipeline: evaluation, module setup, seed, test script, and video proof."""
    bundles_dir, bundle_id = synthesized_demo
    db_file = tmp_path / "test.db"

    with db_session(db_file) as conn:
        instance_repo = InstanceRepository(conn)
        inst = instance_repo.add_instance(
            InstanceCreate(
                id="inst-zurich-poc",
                name="Zurich Healthcare POC",
                url="https://zurich-poc.service-now.com",
                is_default=True,
            )
        )
        # The release is detected at connection (ADR-014); simulate a detected profile.
        instance_repo.save_instance_profile(
            InstanceProfile(instance_id="inst-zurich-poc", release="Zurich")
        )
        inst = instance_repo.get_instance("inst-zurich-poc")
        assert inst is not None

        engine = DemoPipelineEngine(bundles_dir=bundles_dir, conn=conn)
        summary = await engine.run_full_pipeline(
            bundle_id=bundle_id,
            instance=inst,
            fake_mode=True,
            record_video=True,
        )

        assert summary.bundle_id == bundle_id
        assert summary.instance_name == "Zurich Healthcare POC"
        assert len(summary.installed_modules) >= 2
        assert summary.applied_properties_count > 0
        assert summary.seeded_records_count > 0
        assert summary.tested_stages_count > 0
        assert summary.test_passed is True
        assert summary.status == "success"
        assert summary.video_proof_url.startswith(f"/api/demos/{bundle_id}/captures/")
        assert summary.video_proof_filename.endswith(".webm")

        # Verify the video proof artifact on disk is a valid WebM binary
        media_file = bundles_dir / bundle_id / "media" / summary.video_proof_filename
        assert media_file.exists()
        raw_bytes = media_file.read_bytes()
        assert raw_bytes.startswith(b"\x1a\x45\xdf\xa3")  # EBML header
        assert b"webm" in raw_bytes
        assert b"V_VP8" in raw_bytes


def test_agent_tools_pipeline_parity(tmp_path: Path, synthesized_demo, monkeypatch):
    """Test AI tools execute evaluate, module install, runbook test, and pipeline."""
    bundles_dir, bundle_id = synthesized_demo
    db_file = tmp_path / "test.db"

    # Route settings bundles dir to test fixture
    from now_workbench.config.settings import Settings

    monkeypatch.setattr(Settings, "get_bundles_dir", lambda self: bundles_dir)

    with db_session(db_file) as conn:
        instance_repo = InstanceRepository(conn)
        instance_repo.add_instance(
            InstanceCreate(
                id="inst-agent-target",
                name="Agent Primary Target",
                url="https://agent-target.service-now.com",
                is_default=True,
            )
        )
        # The release is detected at connection (ADR-014); simulate a detected profile.
        instance_repo.save_instance_profile(
            InstanceProfile(instance_id="inst-agent-target", release="Zurich")
        )
        ctx = ToolContext(conn=conn, fake_mode=True)

        # 1. evaluate_demo tool
        res_eval = execute_tool(ctx, "evaluate_demo", {"bundle_id": bundle_id})
        assert "Evaluated demo" in res_eval.summary
        assert len(res_eval.tiles) == 1
        assert res_eval.tiles[0].type == "data-table"

        # 2. install_demo_modules tool
        res_mods = execute_tool(ctx, "install_demo_modules", {"bundle_id": bundle_id})
        assert "Activated" in res_mods.summary
        assert len(res_mods.tiles) == 1

        # 3. test_demo_script tool
        res_test = execute_tool(ctx, "test_demo_script", {"bundle_id": bundle_id})
        assert "Verified demo script" in res_test.summary
        assert len(res_test.tiles) == 1
        assert res_test.tiles[0].type == "data-table"

        # 4. run_demo_pipeline tool produces media-player tile
        res_pipe = execute_tool(ctx, "run_demo_pipeline", {"bundle_id": bundle_id})
        assert "Demo pipeline completed" in res_pipe.summary
        assert len(res_pipe.tiles) == 1
        media_tile = res_pipe.tiles[0]
        assert media_tile.type == "media-player"
        assert media_tile.props["media_type"] == "video"
        assert ".webm" in media_tile.props["url"]


def test_cli_pipeline_commands(tmp_path: Path, synthesized_demo, monkeypatch):
    """Test CLI commands for demo evaluate, install-modules, test, and pipeline."""
    bundles_dir, bundle_id = synthesized_demo
    db_file = tmp_path / "test.db"

    from now_workbench.config.settings import Settings
    from now_workbench.db import session as db_session_module

    monkeypatch.setattr(Settings, "get_bundles_dir", lambda self: bundles_dir)
    monkeypatch.setattr(db_session_module, "get_db_path", lambda: db_file)

    with db_session(db_file) as conn:
        instance_repo = InstanceRepository(conn)
        instance_repo.add_instance(
            InstanceCreate(
                id="inst-cli-test",
                name="CLI Test Instance",
                url="https://cli-test.service-now.com",
                is_default=True,
            )
        )
        # The release is detected at connection (ADR-014); simulate a detected profile.
        instance_repo.save_instance_profile(
            InstanceProfile(instance_id="inst-cli-test", release="Zurich")
        )

    runner = CliRunner(env={"COLUMNS": "250"})

    # 1. evaluate
    r_eval = runner.invoke(app, ["demo", "evaluate", bundle_id, "--fake"])
    assert r_eval.exit_code == 0
    assert "Demo Readiness Scorecard" in r_eval.stdout

    # 2. install-modules
    r_mods = runner.invoke(app, ["demo", "install-modules", bundle_id, "--fake"])
    assert r_mods.exit_code == 0
    assert "Modules Installed" in r_mods.stdout or "active" in r_mods.stdout

    # 3. test
    r_test = runner.invoke(app, ["demo", "test", bundle_id, "--fake"])
    assert r_test.exit_code == 0
    assert "Demo Script Test Results" in r_test.stdout

    # 4. pipeline
    r_pipe = runner.invoke(app, ["demo", "pipeline", bundle_id, "--fake"])
    assert r_pipe.exit_code == 0
    assert "Demonstration Pipeline Execution Summary" in r_pipe.stdout
    assert "Watch video proof" in r_pipe.stdout
