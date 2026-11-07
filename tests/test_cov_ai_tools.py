# ============================================================================
# File: tests/test_cov_ai_tools.py
# Description: Coverage tests for the Otto bundle, capture and operations tools
#              (bundles.py, captures.py, operations.py) using in-memory fakes.
# Author: Pierre Grothe
# Date: 2026-11-06
# ============================================================================
"""Coverage tests for the Otto bundle/capture/seed/property tool handlers."""

import shutil
from pathlib import Path
from typing import Any

import pytest

from now_workbench.ai.tools import ToolContext, ToolResult, execute_tool
from now_workbench.capture.models import CaptureArtifact, CaptureRequest
from now_workbench.config.settings import settings
from now_workbench.db import InstanceCreate, InstanceProfile, db_session
from now_workbench.db.models import WorkbenchPreferencesUpdate
from now_workbench.db.repos.instances import InstanceRepository
from now_workbench.db.repos.preferences import PreferencesRepository
from now_workbench.properties.engine import PropertyEngine
from now_workbench.sharing.access import ReadOnlyBundleError

REPO_BUNDLES = Path(__file__).resolve().parent.parent / "bundles"
SAMPLE = "sample-ai-assistant"


@pytest.fixture
def library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Copy the real bundle library into a temp dir and point the settings at it."""
    dest = tmp_path / "bundles"
    shutil.copytree(REPO_BUNDLES, dest)
    monkeypatch.setenv("WORKBENCH_BUNDLES_DIR", str(dest))
    work = tmp_path / "workspace"
    work.mkdir()
    monkeypatch.setattr(settings, "workspace_dir", work)
    with db_session() as conn:
        InstanceRepository(conn).save_instance_profile(
            InstanceProfile(instance_id="default-instance", release="Xanadu")
        )
    return dest


def _run(name: str, args: dict[str, Any], fake: bool = True) -> ToolResult:
    with db_session() as conn:
        return execute_tool(ToolContext(conn=conn, fake_mode=fake), name, args, confirmed=True)


def _ok(name: str, args: dict[str, Any], fake: bool = True) -> ToolResult:
    res = _run(name, args, fake)
    assert res.ok, res.summary
    return res


# --------------------------------------------------------------------- bundles


def test_list_bundles_returns_sorted_table(library: Path) -> None:
    res = _ok("list_bundles", {})
    ids = [row[0] for row in res.data["bundles"]]
    assert SAMPLE in ids and "hr-onboarding-ai" in ids
    assert res.summary == f"{len(ids)} demo bundle(s) installed."
    assert res.tiles[0].id == "tile-bundles"


def test_inspect_bundle_describes_manifest(library: Path) -> None:
    res = _ok("inspect_bundle", {"bundle_id": SAMPLE})
    assert "GenAI Agentic Incident Router" in res.summary
    assert res.tiles[0].id == f"tile-inspect-{SAMPLE}"
    assert "Walkthrough: yes" in res.tiles[0].props["body"]


def test_inspect_bundle_unknown_bundle_fails(library: Path) -> None:
    res = _run("inspect_bundle", {"bundle_id": "nope"})
    assert not res.ok
    assert "Demo bundle 'nope' was not found." in res.summary


def test_clone_bundle_registers_new_bundle(library: Path) -> None:
    res = _ok(
        "clone_bundle",
        {"source_bundle_id": SAMPLE, "new_bundle_id": "my-clone", "new_name": "My Clone"},
    )
    assert res.data == {"bundle_id": "my-clone"}
    assert (library / "my-clone" / "manifest.json").exists()
    assert _ok("inspect_bundle", {"bundle_id": "my-clone"}).ok


def test_export_bundle_writes_archive(library: Path) -> None:
    res = _ok("export_bundle", {"bundle_id": SAMPLE})
    archive = Path(res.data["archive"])
    assert archive.name == f"{SAMPLE}.sn-demo.zip"
    assert archive.exists()


def test_delete_bundle_asks_then_removes(library: Path) -> None:
    _ok("clone_bundle", {"source_bundle_id": SAMPLE, "new_bundle_id": "doomed"})
    with db_session() as conn:
        ctx = ToolContext(conn=conn, fake_mode=True)
        pending = execute_tool(ctx, "delete_bundle", {"bundle_id": "doomed"})
        assert "Permanently delete" in str(pending.tiles[0].props)
        done = execute_tool(ctx, "delete_bundle", {"bundle_id": "doomed"}, confirmed=True)
    assert done.ok and "Deleted bundle 'doomed'" in done.summary
    assert not (library / "doomed").exists()
    assert done.data["remaining"] >= 3


def test_synthesize_bundle_creates_registered_bundle(library: Path) -> None:
    res = _ok("synthesize_bundle", {"use_case": "Automate laptop onboarding"})
    bundle_id = res.data["bundle_id"]
    assert (library / bundle_id / "manifest.json").exists()
    assert "Acme Global" in res.tiles[0].props["body"]
    named = _ok(
        "synthesize_bundle",
        {"use_case": "Track warranty claims", "customer_name": "Zed", "industry": "Retail"},
    )
    assert "Zed" in named.summary


def test_get_runbook_lists_stages(library: Path) -> None:
    res = _ok("get_runbook", {"bundle_id": SAMPLE})
    assert res.summary.startswith("Runbook '")
    assert len(res.data["stages"]) >= 1


def test_get_runbook_without_walkthrough_reports_not_ok(library: Path) -> None:
    shutil.rmtree(library / SAMPLE / "walkthrough")
    res = _run("get_runbook", {"bundle_id": SAMPLE})
    assert not res.ok
    assert res.summary == f"'{SAMPLE}' has no walkthrough guide."


def test_fluent_schema_lists_tables(library: Path) -> None:
    res = _ok("fluent_schema", {"bundle_id": SAMPLE})
    assert res.summary.endswith(f"in '{SAMPLE}'.")
    assert res.data["tables"]


def test_fluent_diff_identical_and_different(library: Path) -> None:
    same = _ok("fluent_diff", {"bundle_id": SAMPLE, "compare_bundle_id": SAMPLE})
    assert same.summary == "Schemas are identical."
    other = _ok("fluent_diff", {"bundle_id": SAMPLE, "compare_bundle_id": "hr-onboarding-ai"})
    assert other.summary == "Schemas differ."
    assert other.data["added_tables"] or other.data["removed_tables"]


def test_fluent_diff_lists_modified_tables(library: Path) -> None:
    _ok("clone_bundle", {"source_bundle_id": SAMPLE, "new_bundle_id": "tweaked"})
    fluent = sorted((library / "tweaked" / "fluent").iterdir())
    target = next(p for p in fluent if p.is_file())
    original = target.read_text(encoding="utf-8")
    target.write_text(original + "\n", encoding="utf-8")
    res = _ok("fluent_diff", {"bundle_id": SAMPLE, "compare_bundle_id": "tweaked"})
    assert res.tiles


def test_list_templates_shows_seeded_template(library: Path) -> None:
    res = _ok("list_templates", {})
    assert ["agentic-router-template"] == [r[0] for r in res.data["templates"]]


def test_generate_from_template_creates_bundle(library: Path) -> None:
    res = _ok(
        "generate_from_template",
        {
            "template_id": "agentic-router-template",
            "new_bundle_id": "acme-router",
            "customer_name": "Acme",
        },
    )
    assert "Generated 'acme-router' for Acme" in res.summary
    assert Path(res.data["bundle_path"]).exists()
    colored = _ok(
        "generate_from_template",
        {
            "template_id": "agentic-router-template",
            "new_bundle_id": "beta-router",
            "customer_name": "Beta",
            "primary_color": "#112233",
        },
    )
    assert colored.ok


def test_generate_from_template_unknown_template_fails(library: Path) -> None:
    res = _run(
        "generate_from_template",
        {"template_id": "zzz", "new_bundle_id": "x", "customer_name": "X"},
    )
    assert not res.ok
    assert "Template 'zzz' not found." in res.summary


class _FakeCaptureEngine:
    """Stands in for the live browser engine: returns a real PNG/WEBM file on disk."""

    media = "screenshot"
    payload = b"\x89PNGdata"
    root: Path

    def __init__(self, bundles_dir: Path) -> None:
        self.bundles_dir = bundles_dir

    async def capture(self, req: CaptureRequest, **_kw: Any) -> CaptureArtifact:
        media = _FakeCaptureEngine.media
        ext = ".png" if media == "screenshot" else ".webm"
        path = _FakeCaptureEngine.root / f"live{ext}"
        path.write_bytes(_FakeCaptureEngine.payload)
        if media == "video":
            path.with_suffix(".png").write_bytes(_FakeCaptureEngine.payload)
        return CaptureArtifact(
            id="cap1",
            bundle_id=req.bundle_id,
            instance_url="https://x.service-now.com",
            target_path=req.target_path,
            media_type=media,
            label=req.label,
            filename=path.name,
            file_path=str(path),
            url=f"/media/{path.name}",
            engine="playwright",
        )


def test_capture_media_simulated_has_no_image(library: Path) -> None:
    res = _ok("capture_media", {"label": "Home", "media_type": "screenshot"})
    assert "SIMULATED placeholder" in res.summary
    assert res.images == []
    assert res.tiles[0].id.startswith("tile-capture-")
    assert res.data["filename"]


def test_capture_media_live_attaches_image(
    library: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "now_workbench.ai.tools.bundles.PlaywrightCaptureEngine", _FakeCaptureEngine
    )
    _FakeCaptureEngine.root = tmp_path
    _FakeCaptureEngine.media = "screenshot"
    _FakeCaptureEngine.payload = b"\x89PNGdata"
    with db_session() as conn:
        PreferencesRepository(conn).update_workbench_preferences(
            WorkbenchPreferencesUpdate(capture_fake_mode=False)
        )
    res = _ok("capture_media", {"bundle_id": SAMPLE, "target_path": "/x"}, fake=False)
    assert "live capture" in res.summary
    assert "The image is attached" in res.summary
    assert len(res.images) == 1


def test_capture_media_live_video_uses_png_poster(
    library: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "now_workbench.ai.tools.bundles.PlaywrightCaptureEngine", _FakeCaptureEngine
    )
    _FakeCaptureEngine.root = tmp_path
    _FakeCaptureEngine.media = "video"
    _FakeCaptureEngine.payload = b"\x89PNGdata"
    with db_session() as conn:
        PreferencesRepository(conn).update_workbench_preferences(
            WorkbenchPreferencesUpdate(capture_fake_mode=False)
        )
    res = _ok("capture_media", {"media_type": "video"}, fake=False)
    assert len(res.images) == 1
    assert res.tiles[0].props["media_type"] == "video"


def test_capture_media_oversized_image_is_not_attached(
    library: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "now_workbench.ai.tools.bundles.PlaywrightCaptureEngine", _FakeCaptureEngine
    )
    _FakeCaptureEngine.root = tmp_path
    _FakeCaptureEngine.media = "screenshot"
    _FakeCaptureEngine.payload = b"0" * 3_600_000
    with db_session() as conn:
        PreferencesRepository(conn).update_workbench_preferences(
            WorkbenchPreferencesUpdate(capture_fake_mode=False)
        )
    res = _ok("capture_media", {}, fake=False)
    assert res.images == []
    assert "live capture" in res.summary


def test_evaluate_demo_builds_scorecard(library: Path) -> None:
    res = _ok("evaluate_demo", {"bundle_id": SAMPLE})
    assert res.summary.startswith(f"Evaluated demo '{SAMPLE}'")
    assert res.tiles[0].id == f"tile-eval-{SAMPLE}"
    assert "required_plugins" in res.data


def test_evaluate_demo_reports_missing_modules(library: Path) -> None:
    res = _ok("evaluate_demo", {"bundle_id": SAMPLE})
    if not res.data["is_ready"]:
        assert "module(s) missing" in res.summary
    else:
        assert res.summary.endswith("ready to deploy.")


def test_install_demo_modules_activates_then_reports_all_active(library: Path) -> None:
    first = _ok("install_demo_modules", {"bundle_id": SAMPLE})
    second = _ok("install_demo_modules", {"bundle_id": SAMPLE})
    if first.data:
        assert first.data["installed_count"] == len(first.data["modules"])
        assert first.summary.startswith("Activated")
    assert second.summary.startswith("All required modules") or second.data


def test_test_demo_script_reports_stage_results(library: Path) -> None:
    res = _ok("test_demo_script", {"bundle_id": SAMPLE})
    assert "stages passed" in res.summary
    assert res.data["total_stages"] >= 1


def test_run_demo_pipeline_without_video_gives_text_tile(library: Path) -> None:
    res = _ok("run_demo_pipeline", {"bundle_id": SAMPLE, "no_video": True})
    assert res.tiles[0].id in {f"tile-pipe-{SAMPLE}", f"tile-proof-{SAMPLE}"}
    assert res.summary == res.data["message"]


def test_run_demo_pipeline_with_video_gives_proof_tile(library: Path) -> None:
    res = _ok("run_demo_pipeline", {"bundle_id": SAMPLE})
    assert res.tiles[0].id in {f"tile-pipe-{SAMPLE}", f"tile-proof-{SAMPLE}"}


def test_update_bundle_accepts_comma_separated_tags(library: Path) -> None:
    res = _ok(
        "update_bundle",
        {"bundle_id": SAMPLE, "name": "Renamed", "description": "New text", "tags": "a, b,,c"},
    )
    assert "Renamed" in res.summary
    assert "Tags: a, b, c" in res.tiles[0].props["body"]


def test_update_bundle_without_tags_keeps_manifest(library: Path) -> None:
    res = _ok("update_bundle", {"bundle_id": SAMPLE, "name": "Only Name"})
    assert res.data["manifest"]["name"] == "Only Name"
    assert res.data["manifest"]["tags"]


# -------------------------------------------------------------------- captures


def test_list_demo_captures_empty(library: Path) -> None:
    (library / SAMPLE / "media" / "captures.json").write_text("[]", encoding="utf-8")
    res = _ok("list_demo_captures", {"bundle_id": SAMPLE})
    assert res.summary == f"No media captures recorded for bundle '{SAMPLE}'."
    assert res.tiles[0].id == f"tile-caps-{SAMPLE}"


def test_capture_lifecycle_list_update_delete(library: Path) -> None:
    (library / SAMPLE / "media" / "captures.json").write_text("[]", encoding="utf-8")
    made = _ok("capture_media", {"bundle_id": SAMPLE, "label": "First"})
    filename = made.data["filename"]

    listed = _ok("list_demo_captures", {"bundle_id": SAMPLE})
    assert listed.summary.startswith(f"Found 1 media capture(s) for '{SAMPLE}'")
    assert listed.data["captures"][0]["filename"] == filename
    assert listed.tiles[1].id.startswith("tile-preview-")

    renamed = _ok(
        "update_demo_capture",
        {"bundle_id": SAMPLE, "filename": filename, "label": "  Renamed  "},
    )
    assert renamed.summary == f"Updated capture '{filename}' label to: 'Renamed'."
    assert renamed.tiles[0].id == f"tile-cap-up-{filename}"

    with db_session() as conn:
        ctx = ToolContext(conn=conn, fake_mode=True)
        args = {"bundle_id": SAMPLE, "filename": filename}
        pending = execute_tool(ctx, "delete_demo_capture", args)
        assert filename in str(pending.tiles[0].props)
        gone = execute_tool(ctx, "delete_demo_capture", args, confirmed=True)
    assert gone.data == {"remaining": 0}
    assert f"Deleted capture '{filename}'" in gone.summary


def test_update_demo_capture_unknown_file_fails(library: Path) -> None:
    res = _run("update_demo_capture", {"bundle_id": SAMPLE, "filename": "x.png", "label": "L"})
    assert not res.ok
    assert "not found" in res.summary


# ------------------------------------------------------------------ operations


def _seed() -> ToolResult:
    return _ok("seed_bundle", {"bundle_id": SAMPLE})


def test_seed_bundle_records_operation(library: Path) -> None:
    res = _seed()
    assert res.data["records"] > 0
    assert f"(operation {res.data['operation_id']})" in res.summary
    hist = _ok("seed_history", {"limit": 5})
    assert hist.summary == "1 seed operation(s) on record."
    assert hist.data["operations"][0][0] == res.data["operation_id"]


def test_rollback_seed_deletes_records_after_confirmation(library: Path) -> None:
    op_id = _seed().data["operation_id"]
    with db_session() as conn:
        ctx = ToolContext(conn=conn, fake_mode=False)
        pending = execute_tool(ctx, "rollback_seed", {"operation_id": op_id})
        assert "Delete" in str(pending.tiles[0].props)
        done = execute_tool(ctx, "rollback_seed", {"operation_id": op_id}, confirmed=True)
    assert done.ok
    assert done.data["errors"] == []
    assert done.data["deleted"] > 0


def test_rollback_seed_unknown_operation_plan_and_result(library: Path) -> None:
    with db_session() as conn:
        ctx = ToolContext(conn=conn, fake_mode=True)
        pending = execute_tool(ctx, "rollback_seed", {"operation_id": "ghost"})
        assert "was not found" in str(pending.tiles[0].props)
        done = execute_tool(ctx, "rollback_seed", {"operation_id": "ghost"}, confirmed=True)
    assert "ghost" in done.summary


def test_verify_seed_operation_checks_each_record(library: Path) -> None:
    op_id = _seed().data["operation_id"]
    res = _run("verify_seed_operation", {"operation_id": op_id}, fake=False)
    assert "record(s) of" in res.summary
    assert res.tiles[0].id == f"tile-verify-{op_id}"
    assert len(res.data["records"]) > 0


def test_verify_seed_operation_unknown_operation(library: Path) -> None:
    res = _run("verify_seed_operation", {"operation_id": "ghost"})
    assert "ghost" in res.summary or not res.ok


def test_reset_demo_rolls_back_and_restores(library: Path) -> None:
    _seed()
    with db_session() as conn:
        ctx = ToolContext(conn=conn, fake_mode=True)
        pending = execute_tool(ctx, "reset_demo", {"bundle_id": SAMPLE})
        assert "Reset demo" in str(pending.tiles[0].props)
        done = execute_tool(ctx, "reset_demo", {"bundle_id": SAMPLE}, confirmed=True)
    assert done.ok
    assert done.data["rolled_back"] > 0


def test_verify_stage_passes_known_stage(library: Path) -> None:
    res = _run("verify_stage", {"bundle_id": SAMPLE, "step_number": 1})
    assert res.summary.startswith("Stage 1 '")
    assert res.tiles[0].id == f"tile-verify-{SAMPLE}-1"


def test_verify_stage_unknown_step_not_ok(library: Path) -> None:
    res = _run("verify_stage", {"bundle_id": SAMPLE, "step_number": 999})
    assert not res.ok
    assert res.summary == f"Stage 999 not found in '{SAMPLE}'."


def test_verify_stage_without_walkthrough_not_ok(library: Path) -> None:
    shutil.rmtree(library / SAMPLE / "walkthrough")
    res = _run("verify_stage", {"bundle_id": SAMPLE, "step_number": 1})
    assert not res.ok
    assert res.summary == f"'{SAMPLE}' has no walkthrough guide."


def test_get_properties_simulated_instance_skips_live_read(library: Path) -> None:
    res = _ok("get_properties", {"bundle_id": SAMPLE})
    assert "live values not read (simulated instance)" in res.summary
    assert res.data["live"] == {}
    assert all(row[2] == "-" for row in res.tiles[0].props["rows"])


def test_get_properties_live_instance_reads_values(
    library: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_live(self: PropertyEngine, names: list[str], inst: Any) -> dict[str, str | None]:
        return {n: ("on" if i == 0 else None) for i, n in enumerate(names)}

    monkeypatch.setattr(PropertyEngine, "read_live_values", fake_live)
    with db_session() as conn:
        InstanceRepository(conn).add_instance(
            InstanceCreate(id="live", name="Live", url="https://live.service-now.com")
        )
    res = _ok("get_properties", {"bundle_id": SAMPLE, "instance": "live"}, fake=False)
    assert "live values read from the instance" in res.summary
    labels = [row[2] for row in res.tiles[0].props["rows"]]
    assert labels[0] == "on"
    assert "(not set)" in labels[1:]


def test_apply_then_restore_properties(library: Path) -> None:
    applied = _ok("apply_properties", {"bundle_id": SAMPLE})
    assert applied.data["applied"] > 0
    assert f"from '{SAMPLE}'" in applied.summary
    with db_session() as conn:
        ctx = ToolContext(conn=conn, fake_mode=True)
        pending = execute_tool(ctx, "restore_properties", {"bundle_id": SAMPLE})
        assert "Restore original" in str(pending.tiles[0].props)
        done = execute_tool(ctx, "restore_properties", {"bundle_id": SAMPLE}, confirmed=True)
    assert done.data["restored"] > 0


def test_seed_history_empty(library: Path) -> None:
    res = _ok("seed_history", {})
    assert res.summary == "0 seed operation(s) on record."


def test_bundle_access_read_only_share_becomes_value_error(
    library: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def read_only(*_a: Any, **_k: Any) -> None:
        raise ReadOnlyBundleError("'x' is shared with you read-only.")

    monkeypatch.setattr("now_workbench.ai.tools.bundles.resolve_bundle", read_only)
    res = _run("update_bundle", {"bundle_id": "x", "name": "N"})
    assert not res.ok
    assert "shared with you read-only" in res.summary
