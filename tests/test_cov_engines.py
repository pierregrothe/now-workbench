# tests/test_cov_engines.py
# Coverage tests for bundle/capture/release/CLI/seed/fluent/plugin engines
# Author: Pierre Grothe
# Date: 2026-11-06
"""Line-coverage tests for the pipeline, capture, release, CLI and engine modules."""

import json
import os
import shutil
import sqlite3
import stat
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from now_workbench.bundles.manager import BundleManager
from now_workbench.bundles.pipeline import DemoPipelineEngine
from now_workbench.capture import driver as driver_mod
from now_workbench.capture import engine as capture_engine_mod
from now_workbench.capture.engine import CaptureFailedError, PlaywrightCaptureEngine
from now_workbench.capture.models import CaptureArtifact, CaptureRequest
from now_workbench.cli import app
from now_workbench.db import (
    DatabaseRepository,
    InstanceCreate,
    InstanceProfile,
    db_session,
    init_db,
)
from now_workbench.db.models import InstanceRecord, SeedOperationRecord, SeedRecordItem
from now_workbench.db.schema import MIGRATIONS, SCHEMA_VERSION
from now_workbench.db.schema import apply_migrations as migrate
from now_workbench.plugins.manager import PluginManager
from now_workbench.releases.compatibility import (
    check_feature_compatibility,
    compare_releases,
    evaluate_release_prerequisites,
    get_release_index,
    is_release_compatible,
)
from now_workbench.releases.workspaces import resolve_workspace, translate_workspace_url
from now_workbench.runbooks.models import RunbookTestResult, StageTestResult
from now_workbench.seed.engine import SeedEngine

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE = "sample-ai-assistant"
runner = CliRunner(env={"COLUMNS": "250"})


@pytest.fixture
def bundles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A private bundles dir holding a copy of the sample bundle."""
    dest = tmp_path / "bundles"
    dest.mkdir()
    shutil.copytree(REPO_ROOT / "bundles" / SAMPLE, dest / SAMPLE)
    monkeypatch.setenv("WORKBENCH_BUNDLES_DIR", str(dest))
    return dest


def _detect_release(release: str = "Zurich", instance_id: str = "default-instance") -> None:
    with db_session() as repo:
        repo.save_instance_profile(InstanceProfile(instance_id=instance_id, release=release))


def _instance(release: str = "Zurich") -> InstanceRecord:
    return InstanceRecord(
        id="i1",
        name="I1",
        url="https://a.service-now.com",
        username="admin",
        password="pw",
        auth_type="basic",
        release=release,
        is_default=True,
    )


def _stub(bin_dir: Path, name: str, body: str) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    path = bin_dir / name
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


# --------------------------------------------------------------------------- pipeline CLI


def test_evaluate_demo_cmd_incompatible_when_release_undetected(bundles: Path) -> None:
    res = runner.invoke(app, ["demo", "evaluate", SAMPLE, "--fake"])
    assert res.exit_code == 0
    assert "INCOMPATIBLE" in res.stdout
    assert "PLATFORM INCOMPATIBLE" in res.stdout


def test_evaluate_demo_cmd_modules_required_then_ready(bundles: Path) -> None:
    _detect_release()
    res = runner.invoke(app, ["demo", "evaluate", SAMPLE, "--fake"])
    assert res.exit_code == 0
    assert "COMPATIBLE" in res.stdout
    assert "MODULES REQUIRED" in res.stdout
    assert runner.invoke(app, ["demo", "install-modules", SAMPLE, "--fake"]).exit_code == 0
    again = runner.invoke(app, ["demo", "evaluate", SAMPLE, "--fake"])
    assert "READY TO DEPLOY" in again.stdout


def test_evaluate_demo_cmd_unknown_instance_exits_1(bundles: Path) -> None:
    res = runner.invoke(app, ["demo", "evaluate", SAMPLE, "-i", "nope", "--fake"])
    assert res.exit_code == 1
    assert "Target instance not found" in res.stdout


def test_evaluate_demo_cmd_unknown_bundle_exits_1(bundles: Path) -> None:
    res = runner.invoke(app, ["demo", "evaluate", "ghost", "--fake"])
    assert res.exit_code == 1
    assert "Evaluation error" in res.stdout


def test_install_modules_cmd_reports_installed_then_nothing_to_do(bundles: Path) -> None:
    first = runner.invoke(app, ["demo", "install-modules", SAMPLE, "--fake"])
    assert first.exit_code == 0
    assert "Modules Installed" in first.stdout
    second = runner.invoke(app, ["demo", "install-modules", SAMPLE, "--fake"])
    assert second.exit_code == 0
    assert "are active on" in second.stdout


def test_install_modules_cmd_unknown_bundle_exits_1(bundles: Path) -> None:
    res = runner.invoke(app, ["demo", "install-modules", "ghost", "--fake"])
    assert res.exit_code == 1
    assert "Plugin installation error" in res.stdout


def test_test_demo_cmd_unknown_bundle_exits_1(bundles: Path) -> None:
    res = runner.invoke(app, ["demo", "test", "ghost", "--fake"])
    assert res.exit_code == 1
    assert "Test execution error" in res.stdout


def test_test_demo_cmd_failed_stage_exits_1(bundles: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    async def failing(
        self: DemoPipelineEngine, bundle_id: str, instance: InstanceRecord, fake_mode: bool = False
    ) -> RunbookTestResult:
        stage = StageTestResult(
            step_number=1, title="S", target_table=None, passed=False, message="no"
        )
        return RunbookTestResult(
            bundle_id=bundle_id,
            instance_name=instance.name,
            total_stages=1,
            passed_stages=0,
            all_passed=False,
            stages=[stage],
        )

    monkeypatch.setattr(DemoPipelineEngine, "test_demo_script", failing)
    res = runner.invoke(app, ["demo", "test", SAMPLE, "--fake"])
    assert res.exit_code == 1
    assert "Passed 0/1 stages" in res.stdout
    assert "FAIL" in res.stdout


def test_pipeline_demo_cmd_unknown_bundle_exits_1(bundles: Path) -> None:
    res = runner.invoke(app, ["demo", "pipeline", "ghost", "--fake"])
    assert res.exit_code == 1
    assert "Pipeline execution error" in res.stdout


def test_pipeline_demo_cmd_no_video_omits_video_row(bundles: Path) -> None:
    _detect_release()
    res = runner.invoke(app, ["demo", "pipeline", SAMPLE, "--fake", "--no-video"])
    assert res.exit_code == 0
    assert "Video Proof" not in res.stdout


def test_delete_demo_cmd_flows(bundles: Path) -> None:
    declined = runner.invoke(app, ["demo", "delete", SAMPLE], input="n\n")
    assert "Deletion cancelled" in declined.stdout
    assert (bundles / SAMPLE).is_dir()
    confirmed = runner.invoke(app, ["demo", "delete", SAMPLE], input="y\n")
    assert "deleted" in confirmed.stdout
    assert not (bundles / SAMPLE).exists()
    missing = runner.invoke(app, ["demo", "delete", SAMPLE, "--force"])
    assert missing.exit_code == 1
    assert "Error deleting bundle" in missing.stdout


def test_update_demo_cmd_updates_manifest_and_reports_errors(bundles: Path) -> None:
    ok = runner.invoke(
        app, ["demo", "update", SAMPLE, "--name", "Renamed", "--tags", "a, b,,c", "--desc", "d"]
    )
    assert ok.exit_code == 0
    manifest = json.loads((bundles / SAMPLE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "Renamed"
    assert manifest["tags"] == ["a", "b", "c"]
    assert manifest["description"] == "d"
    bad = runner.invoke(app, ["demo", "update", "ghost", "--name", "x"])
    assert bad.exit_code == 1
    assert "Error updating bundle" in bad.stdout


def _write_capture(bundles: Path, name: str = "cap-1.png", label: str = "L") -> None:
    media = bundles / SAMPLE / "media"
    media.mkdir(exist_ok=True)
    (media / name).write_bytes(b"x")
    art = CaptureArtifact(
        id=Path(name).stem,
        bundle_id=SAMPLE,
        instance_url="u",
        target_path="/p",
        media_type="screenshot",
        label=label,
        filename=name,
        file_path=str(media / name),
        url=f"/api/demos/{SAMPLE}/captures/{name}",
    )
    index = media / "captures.json"
    existing = json.loads(index.read_text(encoding="utf-8")) if index.exists() else []
    index.write_text(json.dumps([*existing, art.model_dump()]), encoding="utf-8")


def test_capture_cmds_list_update_delete(bundles: Path) -> None:
    empty = runner.invoke(app, ["demo", "list-captures", "nocaps"])
    assert "No captures found" in empty.stdout
    _write_capture(bundles)
    _write_capture(bundles, "cap-2.png")
    listed = runner.invoke(app, ["demo", "list-captures", SAMPLE])
    assert "cap-1.png" in listed.stdout
    upd = runner.invoke(app, ["demo", "update-capture", SAMPLE, "cap-1.png", "--label", "New"])
    assert upd.exit_code == 0
    assert "New" in upd.stdout
    bad = runner.invoke(app, ["demo", "update-capture", SAMPLE, "zzz.png", "--label", "x"])
    assert bad.exit_code == 1
    assert "Error updating capture" in bad.stdout
    one = runner.invoke(app, ["demo", "delete-capture", SAMPLE, "cap-1.png"])
    assert "Deleted capture artifact" in one.stdout
    assert not (bundles / SAMPLE / "media" / "cap-1.png").exists()
    none = runner.invoke(app, ["demo", "delete-capture", SAMPLE])
    assert none.exit_code == 1
    assert "Specify a filename" in none.stdout
    missing = runner.invoke(app, ["demo", "delete-capture", SAMPLE, "nope.png"])
    assert missing.exit_code == 1
    assert "Error deleting capture" in missing.stdout
    cleared = runner.invoke(app, ["demo", "delete-capture", SAMPLE, "--all"])
    assert "Cleared all" in cleared.stdout


# --------------------------------------------------------------------------- pipeline engine


def test_get_bundle_path_missing_raises(bundles: Path) -> None:
    with db_session() as repo:
        engine = DemoPipelineEngine(bundles_dir=bundles, repo=repo)
        with pytest.raises(FileNotFoundError, match="not found"):
            engine._get_bundle_path("ghost")


def test_evaluate_bundle_ignores_unreadable_seed_files(bundles: Path) -> None:
    seed = bundles / SAMPLE / "seed"
    seed.mkdir(exist_ok=True)
    (seed / "zz_broken.json").write_text("{not json", encoding="utf-8")
    (seed / "zz_obj.json").write_text('{"a": 1}', encoding="utf-8")
    (seed / "zz_mixed.json").write_text('[1, {"table": "zz_tbl"}]', encoding="utf-8")
    with db_session() as repo:
        engine = DemoPipelineEngine(bundles_dir=bundles, repo=repo)
        inst = repo.get_default_instance()
        assert inst is not None
        res = engine.evaluate_bundle(SAMPLE, inst, fake_mode=True)
    assert "zz_tbl" in res.target_tables


async def test_test_demo_script_without_runbook_passes_empty(
    bundles: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with db_session() as repo:
        engine = DemoPipelineEngine(bundles_dir=bundles, repo=repo)
        monkeypatch.setattr(engine.runbook_engine, "load_runbook", lambda *a, **k: None)
        inst = repo.get_default_instance()
        assert inst is not None
        res = await engine.test_demo_script(SAMPLE, inst, fake_mode=True)
    assert res.total_stages == 0
    assert res.all_passed is True


async def test_run_full_pipeline_incompatible_release_aborts(bundles: Path) -> None:
    with db_session() as repo:
        engine = DemoPipelineEngine(bundles_dir=bundles, repo=repo)
        inst = repo.get_default_instance()
        assert inst is not None
        summary = await engine.run_full_pipeline(SAMPLE, inst, fake_mode=True, record_video=False)
    assert summary.status == "incompatible"
    assert summary.message.startswith("Pipeline aborted")


async def test_run_full_pipeline_video_failure_is_reported_partial(
    bundles: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def boom(self: DemoPipelineEngine, **_kw: object) -> CaptureArtifact:
        raise CaptureFailedError("no chrome")

    monkeypatch.setattr(DemoPipelineEngine, "record_video_proof", boom)
    _detect_release()
    with db_session() as repo:
        engine = DemoPipelineEngine(bundles_dir=bundles, repo=repo)
        inst = repo.get_default_instance()
        assert inst is not None
        summary = await engine.run_full_pipeline(SAMPLE, inst, fake_mode=True, record_video=True)
    assert summary.status == "partial"
    assert "Video proof not recorded: no chrome" in summary.message
    assert summary.video_proof_url == ""


async def test_run_full_pipeline_missing_plugin_reports_partial(bundles: Path) -> None:
    _detect_release()

    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with db_session() as repo:
        engine = DemoPipelineEngine(bundles_dir=bundles, repo=repo)
        engine.plugin_manager = PluginManager(repo, transport=httpx.MockTransport(refuse))
        inst = repo.get_default_instance()
        assert inst is not None
        live = inst.model_copy(update={"url": "https://live.service-now.com"})
        eval_res = engine.evaluate_bundle(SAMPLE, live)
        assert eval_res.missing_plugins
        installed = engine.install_required_modules(SAMPLE, live)
    assert installed == []


# --------------------------------------------------------------------------- bundle manager


def test_inspect_bundle_tolerates_corrupt_properties_and_captures(bundles: Path) -> None:
    props = bundles / SAMPLE / "properties"
    props.mkdir(exist_ok=True)
    (props / "sys_properties.json").write_text("{bad", encoding="utf-8")
    media = bundles / SAMPLE / "media"
    media.mkdir(exist_ok=True)
    (media / "captures.json").write_text("[bad", encoding="utf-8")
    info = BundleManager(storage_dir=bundles).inspect_bundle(bundles / SAMPLE)
    assert info.manifest.id == SAMPLE


def test_update_bundle_manifest_missing_files_raise(bundles: Path) -> None:
    mgr = BundleManager(storage_dir=bundles)
    with pytest.raises(FileNotFoundError, match="does not exist"):
        mgr.update_bundle_manifest("ghost", name="x")
    (bundles / SAMPLE / "manifest.json").unlink()
    with pytest.raises(FileNotFoundError, match="manifest.json missing"):
        mgr.update_bundle_manifest(SAMPLE, name="x")


# --------------------------------------------------------------------------- capture engine


async def test_run_chrome_capture_script_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_file = tmp_path / "a" / "b" / "c" / "engine.py"
    monkeypatch.setattr(capture_engine_mod, "__file__", str(fake_file))
    ok, why = await capture_engine_mod._run_chrome_capture(
        "https://x", tmp_path / "o.png", "screenshot", 10, 10
    )
    assert ok is False
    assert "not installed" in why


async def test_run_chrome_capture_node_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    ok, why = await capture_engine_mod._run_chrome_capture(
        "https://x", tmp_path / "o.png", "screenshot", 10, 10
    )
    assert (ok, why) == (False, "Node.js is not installed on the server")


async def test_run_chrome_capture_unstartable_node(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub(tmp_path / "bin", "node", "#!/nonexistent/interpreter\n")
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}:/bin:/usr/bin")
    ok, why = await capture_engine_mod._run_chrome_capture(
        "https://x", tmp_path / "o.png", "screenshot", 10, 10
    )
    assert ok is False
    assert why.startswith("could not start the browser")


async def test_run_chrome_capture_failure_reports_last_stderr_line_or_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}:/bin:/usr/bin")
    _stub(
        tmp_path / "bin",
        "node",
        "#!/bin/sh\ncat >/dev/null\necho first >&2\necho last >&2\nexit 2\n",
    )
    ok, why = await capture_engine_mod._run_chrome_capture(
        "https://x", tmp_path / "o.png", "screenshot", 10, 10
    )
    assert (ok, why) == (False, "last")
    _stub(tmp_path / "bin", "node", "#!/bin/sh\ncat >/dev/null\nexit 4\n")
    ok, why = await capture_engine_mod._run_chrome_capture(
        "https://x", tmp_path / "o.png", "screenshot", 10, 10
    )
    assert why == "the browser exited with code 4"


def test_capture_engine_index_operations(tmp_path: Path) -> None:
    eng = PlaywrightCaptureEngine(bundles_dir=tmp_path)
    media = tmp_path / "b" / "media"
    media.mkdir(parents=True)
    for bad in ("", "a/b.png", "a\\b.png", "..x"):
        with pytest.raises(ValueError, match="Invalid capture filename"):
            eng.delete_capture("b", bad)
        with pytest.raises(ValueError, match="Invalid capture filename"):
            eng.update_capture("b", bad, "x")
    for bad_id in ("", "a/b", "a\\b", ".."):
        with pytest.raises(ValueError, match="Invalid bundle ID"):
            eng.clear_all_captures(bad_id)
    with pytest.raises(FileNotFoundError):
        eng.delete_capture("b", "ghost.png")
    with pytest.raises(FileNotFoundError, match="not found"):
        eng.update_capture("b", "ghost.png", "x")
    (media / "keep.png").write_bytes(b"1")
    (media / "keep.webm").write_bytes(b"1")
    (media / "keep.txt").write_text("t", encoding="utf-8")
    assert eng.clear_all_captures("b") == 2
    assert (media / "keep.txt").exists()
    assert eng.list_captures("b") == []


def test_delete_capture_removes_orphan_file_and_companions(tmp_path: Path) -> None:
    eng = PlaywrightCaptureEngine(bundles_dir=tmp_path)
    media = tmp_path / "b" / "media"
    media.mkdir(parents=True)
    (media / "orphan.png").write_bytes(b"1")
    (media / "orphan.jpg").write_bytes(b"1")
    assert eng.delete_capture("b", "orphan.png") is True
    assert not (media / "orphan.jpg").exists()
    (media / "only.jpg").write_bytes(b"1")
    assert eng.delete_capture("b", "only.png") is True


async def test_capture_video_playbook_failure_names_failed_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def failed(*_a: object, **_k: object) -> tuple[bool, bool, list[dict[str, object]]]:
        return False, False, [{"status": "failed", "description": "go", "error_message": "bad"}]

    monkeypatch.setattr(capture_engine_mod, "_execute_video_playbook", failed)
    eng = PlaywrightCaptureEngine(bundles_dir=tmp_path)
    req = CaptureRequest(bundle_id="b", target_path="/x", media_type="video")
    with pytest.raises(CaptureFailedError, match=r"go \(bad\)"):
        await eng.capture(req, instance_url="https://x")
    assert eng.list_captures("b") == []


async def test_capture_video_playbook_success_is_labelled_native(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def ok(*_a: object, **_k: object) -> tuple[bool, bool, list[dict[str, object]]]:
        return True, True, [{"status": "passed"}]

    monkeypatch.setattr(capture_engine_mod, "_execute_video_playbook", ok)
    eng = PlaywrightCaptureEngine(bundles_dir=tmp_path)
    req = CaptureRequest(bundle_id="b", target_path="/x", media_type="video")
    art = await eng.capture(req, instance_url="https://x/")
    assert art.engine == "google-chrome-native"
    assert art.live_authenticated is True


async def test_capture_fake_mode_writes_labelled_placeholder(tmp_path: Path) -> None:
    eng = PlaywrightCaptureEngine(bundles_dir=tmp_path)
    for media_type, magic in (("screenshot", b"\x89PNG"), ("video", b"\x1a\x45\xdf\xa3")):
        req = CaptureRequest(bundle_id="b", target_path="x", media_type=media_type, fake_mode=True)
        art = await eng.capture(req, instance_url="https://x")
        assert art.engine == "playwright-simulated"
        assert Path(art.file_path).read_bytes().startswith(magic)


# --------------------------------------------------------------------------- capture driver


def _playbook() -> object:
    return driver_mod.load_playbook(Path("/nonexistent"), "bid")


def test_load_playbook_valid_and_corrupt_file(tmp_path: Path) -> None:
    walk = tmp_path / "walkthrough"
    walk.mkdir()
    default = driver_mod.load_playbook(tmp_path, "bid")
    (walk / "playbook.json").write_text(default.model_dump_json(), encoding="utf-8")
    assert driver_mod.load_playbook(tmp_path, "bid") == default
    (walk / "playbook.json").write_text("{nope", encoding="utf-8")
    assert driver_mod.load_playbook(tmp_path, "bid").bundle_id == "bid"


def test_read_and_cleanup_log_handles_garbage_and_cleans_files(tmp_path: Path) -> None:
    log = tmp_path / "l.json"
    pb = tmp_path / "p.json"
    log.write_text("garbage", encoding="utf-8")
    pb.write_text("{}", encoding="utf-8")
    assert driver_mod._read_and_cleanup_log(log, pb) is None
    assert not log.exists()
    assert not pb.exists()


async def test_execute_playbook_fake_mode_succeeds(tmp_path: Path) -> None:
    drv = driver_mod.PlaywrightPlaybookDriver(data_dir=tmp_path / "data")
    pb = driver_mod.load_playbook(tmp_path, "bid")
    res = await drv.execute_playbook(
        pb, _instance(), tmp_path / "v.webm", tmp_path / "v.png", fake_mode=True
    )
    assert res.success is True
    assert res.total_steps == len(pb.steps)


async def test_execute_playbook_returns_runner_log_when_valid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub(
        tmp_path / "bin",
        "node",
        '#!/bin/sh\ncat >/dev/null\nwhile [ $# -gt 0 ]; do [ "$1" = --output-log ] && '
        'log="$2"; shift; done\n'
        'printf \'{"bundle_id":"bid","playbook_title":"T","success":true,"total_steps":1,'
        '"passed_steps":1,"step_results":[],"duration_ms":1,"started_at":"s",'
        '"completed_at":"c"}\' > "$log"\nexit 0\n',
    )
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}:/bin:/usr/bin")
    drv = driver_mod.PlaywrightPlaybookDriver(data_dir=tmp_path / "data")
    pb = driver_mod.load_playbook(tmp_path, "bid").model_copy(update={"start_path": "rel"})
    res = await drv.execute_playbook(pb, _instance(), tmp_path / "v.webm", tmp_path / "v.png")
    assert res.success is True
    assert res.passed_steps == 1


async def test_execute_playbook_without_log_reports_failure_with_existing_media(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub(tmp_path / "bin", "node", "#!/bin/sh\ncat >/dev/null\nexit 0\n")
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}:/bin:/usr/bin")
    video, image = tmp_path / "v.webm", tmp_path / "v.png"
    video.write_bytes(b"1")
    image.write_bytes(b"1")
    drv = driver_mod.PlaywrightPlaybookDriver(data_dir=tmp_path / "data")
    pb = driver_mod.load_playbook(tmp_path, "bid")
    res = await drv.execute_playbook(pb, _instance(), video, image)
    assert res.success is False
    assert res.video_file == str(video)
    assert res.thumbnail_file == str(image)
    assert "no valid result log" in (res.step_results[0].error_message or "")
    assert res.step_results[1].status == "skipped"


# --------------------------------------------------------------------------- releases


def test_release_compatibility_helpers() -> None:
    assert get_release_index("Zurich") > get_release_index("Utah")
    assert get_release_index("") == -1
    assert get_release_index("Zzzz") > get_release_index("Zurich")
    assert compare_releases("Utah", "Zurich") == -1
    assert compare_releases("Zurich", "Utah") == 1
    assert compare_releases("Zurich", "Zurich") == 0
    assert is_release_compatible("", "Utah") is False
    assert is_release_compatible("Zurich", "Utah") is True


def test_check_feature_compatibility_branches() -> None:
    ok, msg = check_feature_compatibility("plain widget", "Zurich")
    assert ok is True
    assert "no specific release constraint" in msg
    from now_workbench.releases.compatibility import FEATURE_MINIMUM_RELEASES

    feat, (min_rel, _why) = next(iter(FEATURE_MINIMUM_RELEASES.items()))
    ok_new, msg_new = check_feature_compatibility(feat, "Zurich")
    assert ok_new is True
    assert "supported" in msg_new
    bad, msg_bad = check_feature_compatibility(feat, "Rome")
    assert bad is False
    assert min_rel in msg_bad


def test_evaluate_release_prerequisites_reasons() -> None:
    undetected = evaluate_release_prerequisites("", "Utah")
    assert undetected.is_compatible is False
    assert "not been detected" in undetected.reason
    below = evaluate_release_prerequisites("Rome", "Zurich")
    assert "below the required minimum" in below.reason
    missing = evaluate_release_prerequisites("Vancouver", "Rome", tags=["AI Agent Studio"])
    assert missing.is_compatible is False
    assert missing.unsupported_features == ["AI Agent Studio"]
    assert missing.required_features == ["AI Agent Studio"]
    assert "missing capabilities" in missing.reason
    fine = evaluate_release_prerequisites("Zurich", "Utah", tags=["unrelated"])
    assert fine.is_compatible is True
    assert "Release verified" in fine.reason


@pytest.mark.parametrize(
    ("wtype", "release", "name"),
    [
        ("itsm", "Rome", "Agent Workspace"),
        ("sow", "Zurich", "Service Operations Workspace"),
        ("csm", "Rome", "Customer Service Workspace"),
        ("case", "Zurich", "Configurable CSM Workspace"),
        ("ai_studio", "Rome", "Not Available (Pre-Xanadu)"),
        ("now_assist", "Zurich", "AI Agent Studio"),
        ("hr", "Zurich", "Employee Center Workspace"),
        ("other", "Rome", "Classic UI16 Navigation"),
        ("other", "Zurich", "Next Experience Navigation"),
    ],
)
def test_resolve_workspace_by_type_and_release(wtype: str, release: str, name: str) -> None:
    assert resolve_workspace(wtype, release).display_name == name


def test_translate_workspace_url_branches() -> None:
    assert translate_workspace_url("@workspace/itsm/x", "Zurich") == "/now/sow/x"
    assert translate_workspace_url("@workspace/csm/x", "Zurich") == "/now/csm/x"
    assert translate_workspace_url("@workspace/ai_studio/x", "Zurich") == "/now/now-assist-admin/x"
    old = translate_workspace_url("/now/nav/ui/classic/params/target/a", "Rome")
    assert old == "/nav_to.do?uri=a"
    assert translate_workspace_url("/now/sow/rec", "Rome") == "/now/workspace/agent/rec"
    assert translate_workspace_url("/plain", "Rome") == "/plain"
    assert translate_workspace_url("/now/sow/rec", "Zurich") == "/now/sow/rec"


# --------------------------------------------------------------------------- seed / plugins


def _seed_repo() -> DatabaseRepository:
    repo = DatabaseRepository(init_db(":memory:"))
    repo.add_instance(
        InstanceCreate(
            id="inst",
            name="Inst",
            url="https://inst.service-now.com",
            username="a",
            password="p",
            is_default=True,
        )
    )
    return repo


async def test_seed_verify_branches() -> None:
    repo = _seed_repo()

    def handler(request: httpx.Request) -> httpx.Response:
        if "gone" in request.url.path:
            return httpx.Response(404)
        if "boom" in request.url.path:
            raise httpx.ConnectError("down")
        return httpx.Response(200, json={"result": {"number": "INC1", "sys_id": "x"}})

    items = [
        SeedRecordItem(table="incident", sys_id="here"),
        SeedRecordItem(table="incident", sys_id="gone"),
        SeedRecordItem(table="incident", sys_id="boom"),
    ]
    repo.record_seed_operation(
        SeedOperationRecord(id="op", bundle_id="b", instance_id="inst", created_records=items)
    )
    engine = SeedEngine(repo, transport=httpx.MockTransport(handler))
    out = await engine.verify("op")
    assert [(ok, why[:12]) for _i, ok, why in out] == [
        (True, "INC1"),
        (False, "HTTP 404"),
        (False, "could not as"),
    ]
    with pytest.raises(ValueError, match="not found"):
        await engine.verify("missing")
    simulated = await SeedEngine(repo, fake_mode=True).verify("op")
    assert all(ok and why == "simulated" for _i, ok, why in simulated)


def test_plugin_manager_evaluate_and_install_paths() -> None:
    repo = _seed_repo()
    inst = repo.get_instance("inst")
    assert inst is not None

    def handler(request: httpx.Request) -> httpx.Response:
        pid = request.url.params["sysparm_query"].split("=")[1]
        if pid == "bad.status":
            return httpx.Response(503)
        if pid == "bad.json":
            return httpx.Response(200, text="not json")
        if pid == "inactive":
            return httpx.Response(200, json={"result": [{"active": "inactive"}]})
        return httpx.Response(200, json={"result": [{"active": "active"}]})

    mgr = PluginManager(repo, transport=httpx.MockTransport(handler))
    res = mgr.evaluate_plugins(inst, ["com.snc.incident", "", "bad.status", "bad.json", "inactive"])
    assert res.installed == ["com.snc.incident"]
    assert res.missing == ["bad.status", "bad.json", "inactive"]
    assert "HTTP 503" in res.reasons["bad.status"]
    assert "could not query" in res.reasons["bad.json"]
    assert res.all_satisfied is False
    # Already recorded: a second evaluation takes the 'recorded' branch without re-adding.
    again = mgr.evaluate_plugins(inst, ["com.snc.incident"])
    assert again.all_satisfied is True
    ok, msg = mgr.install_plugin(inst, "inactive")
    assert ok is False
    assert "not active" in msg
    ok2, msg2 = mgr.install_plugin(inst, "com.sn_hr_core")
    assert ok2 is True
    assert "already active" in msg2
    recs, msgs = mgr.install_required_plugins(inst, ["inactive"])
    assert recs == []
    assert len(msgs) == 1


# --------------------------------------------------------------------------- schema


def test_migrate_current_newer_and_broken_fk() -> None:
    conn = sqlite3.connect(":memory:")
    assert migrate(conn) == SCHEMA_VERSION
    assert migrate(conn) == SCHEMA_VERSION
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
    with pytest.raises(RuntimeError, match="newer than this build"):
        migrate(conn)
    conn.close()
    assert len(MIGRATIONS) == SCHEMA_VERSION


def test_migrate_reports_broken_foreign_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = sqlite3.connect(":memory:")
    migrate(conn)
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("CREATE TABLE zp (id INTEGER PRIMARY KEY)")
    conn.execute("CREATE TABLE zc (pid INTEGER REFERENCES zp(id))")
    conn.execute("INSERT INTO zc VALUES (99)")
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION - 1}")
    from now_workbench.db import schema as schema_mod

    patched = (*MIGRATIONS[: SCHEMA_VERSION - 1], "SELECT 1;")
    monkeypatch.setattr(schema_mod, "MIGRATIONS", patched)
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")
    with pytest.raises(RuntimeError, match="broken foreign key"):
        migrate(conn)
    assert bool(conn.execute("PRAGMA foreign_keys").fetchone()[0]) is True
    conn.close()
    assert os.environ.get("PATH") is not None
