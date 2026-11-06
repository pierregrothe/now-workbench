# tests/test_cov_engines_2.py
# Coverage tests (part 2): CLI, instances, synthesizer, remediation, fluent, chat files, seed
# Author: Pierre Grothe
# Date: 2026-11-06
"""Line-coverage tests for the CLI entry points, synthesizer, remediation, fluent and seed."""

import json
import shutil
import stat
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from now_workbench import cli as cli_mod
from now_workbench.bundles import pipeline as pipeline_mod
from now_workbench.bundles.manager import BundleManager
from now_workbench.bundles.pipeline import DemoPipelineEngine, PipelineStepError
from now_workbench.capture import driver as driver_mod
from now_workbench.chat import files as files_mod
from now_workbench.chat.models import Attachment, ConversationLimits
from now_workbench.cli import app
from now_workbench.config.settings import settings
from now_workbench.db import (
    DatabaseRepository,
    InstanceCreate,
    InstanceProfile,
    db_session,
    init_db,
)
from now_workbench.db.models import ChatMessageRecord, ChatThreadRecord, SeedRecordItem
from now_workbench.fluent.engine import FluentEngine
from now_workbench.remediation import (
    RemediationAction,
    RemediationPlan,
    execute_remediation,
    inspect_remediation_needs,
    remediate_directories,
    remediate_env_file,
    remediate_sdk,
)
from now_workbench.runbooks.engine import RunbookEngine
from now_workbench.sdk.runner import SdkExecutionResult
from now_workbench.seed.engine import SeedEngine, SeedPayloadError
from now_workbench.synthesizer.engine import UseCaseSynthesizer
from now_workbench.synthesizer.models import UseCaseSynthesisRequest

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


def _stub(bin_dir: Path, name: str, body: str) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    path = bin_dir / name
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _repo() -> DatabaseRepository:
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


# --------------------------------------------------------------------------- pipeline


class _OkRunner:
    def __init__(self, fake_mode: bool = False) -> None:
        self.fake_mode = fake_mode

    async def deploy(self, **_kw: object) -> SdkExecutionResult:
        return SdkExecutionResult(command="deploy", exit_code=0, output="ok", success=True)


class _BadRunner(_OkRunner):
    async def deploy(self, **_kw: object) -> SdkExecutionResult:
        return SdkExecutionResult(command="deploy", exit_code=2, output=" boom ", success=False)


async def test_deploy_and_seed_deploys_when_project_present(
    bundles: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (bundles / SAMPLE / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(pipeline_mod, "NowSdkRunner", _OkRunner)
    with db_session() as repo:
        inst = repo.get_default_instance()
        assert inst is not None
        engine = DemoPipelineEngine(bundles_dir=bundles, repo=repo)
        seed, note, _renames = await engine.deploy_and_seed(SAMPLE, inst, fake_mode=True)
        assert note == "Fluent app deployed."
        assert seed.status == "completed"
        monkeypatch.setattr(pipeline_mod, "NowSdkRunner", _BadRunner)
        with pytest.raises(PipelineStepError, match="exit code 2.*boom"):
            await engine.deploy_and_seed(SAMPLE, inst, fake_mode=True)


async def test_full_pipeline_with_fake_video_succeeds(bundles: Path) -> None:
    with db_session() as repo:
        repo.save_instance_profile(
            InstanceProfile(instance_id="default-instance", release="Zurich")
        )
        inst = repo.get_default_instance()
        assert inst is not None
        engine = DemoPipelineEngine(bundles_dir=bundles, repo=repo)
        summary = await engine.run_full_pipeline(SAMPLE, inst, fake_mode=True, record_video=True)
    assert summary.status == "success"
    assert summary.video_proof_filename.endswith(".webm")
    assert "Video proof recorded" in summary.message


def test_pipeline_cli_full_run_prints_video_row(bundles: Path) -> None:
    with db_session() as repo:
        repo.save_instance_profile(
            InstanceProfile(instance_id="default-instance", release="Zurich")
        )
    res = runner.invoke(app, ["demo", "pipeline", SAMPLE, "--fake"])
    assert res.exit_code == 0
    assert "Video Proof" in res.stdout
    assert "Watch video proof" in res.stdout


# --------------------------------------------------------------------------- driver


async def test_run_runner_failure_without_log_reports_stderr(tmp_path: Path) -> None:
    script = tmp_path / "fail.sh"
    script.write_text("#!/bin/sh\ncat >/dev/null\necho bad-thing >&2\nexit 5\n", encoding="utf-8")
    script.chmod(0o755)
    inst = InstanceCreate(id="i", name="n", url="https://x")
    record = DatabaseRepository(init_db(":memory:")).add_instance(inst)
    err = await driver_mod._run_runner([str(script)], record)
    assert err is not None
    assert "code 5" in err
    assert "bad-thing" in err
    ok = tmp_path / "ok.sh"
    ok.write_text("#!/bin/sh\ncat >/dev/null\nexit 0\n", encoding="utf-8")
    ok.chmod(0o755)
    assert await driver_mod._run_runner([str(ok)], record) is None
    assert "could not be started" in (
        await driver_mod._run_runner([str(tmp_path / "no")], record) or ""
    )


def test_build_runner_cmd_fake_flag_precedes_credentials_flag(tmp_path: Path) -> None:
    record = DatabaseRepository(init_db(":memory:")).add_instance(
        InstanceCreate(id="i", name="n", url="https://x")
    )
    args = (tmp_path / "s", tmp_path / "p", "https://x/", tmp_path / "v", tmp_path / "i")
    cmd = driver_mod._build_runner_cmd(
        *args, tmp_path / "l", tmp_path / "st", 10, 20, record, fake_mode=True
    )
    assert cmd[-2:] == ["--fake", "--credentials-stdin"]
    assert cmd[cmd.index("--width") + 1] == "10"
    plain = driver_mod._build_runner_cmd(
        *args, tmp_path / "l", tmp_path / "st", 10, 20, record, fake_mode=False
    )
    assert "--fake" not in plain


# --------------------------------------------------------------------------- bundle manager


def test_bundle_manager_list_export_import_clone_delete(bundles: Path, tmp_path: Path) -> None:
    mgr = BundleManager(storage_dir=bundles)
    (bundles / "broken").mkdir()
    (bundles / "broken" / "manifest.json").write_text("{bad", encoding="utf-8")
    (bundles / "notabundle").mkdir()
    assert [b.manifest.id for b in mgr.list_bundles()] == [SAMPLE]
    with pytest.raises(FileNotFoundError):
        mgr.inspect_bundle(bundles / "notabundle")
    archive = mgr.export_bundle(SAMPLE, tmp_path / "out" / "x.zip")
    with pytest.raises(FileNotFoundError):
        mgr.export_bundle("ghost", tmp_path / "y.zip")
    with pytest.raises(FileNotFoundError):
        mgr.import_bundle(tmp_path / "missing.zip")
    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("readme.txt", "x")
    with pytest.raises(ValueError, match="missing required manifest"):
        mgr.import_bundle(bad_zip)
    assert mgr.import_bundle(archive).manifest.id == SAMPLE
    with pytest.raises(ValueError, match="empty"):
        mgr.clone_bundle(SAMPLE, "  ")
    with pytest.raises(FileNotFoundError):
        mgr.clone_bundle("ghost", "t1")
    with pytest.raises(FileExistsError):
        mgr.clone_bundle(SAMPLE, SAMPLE)
    assert mgr.clone_bundle(SAMPLE, "T1", target_name=" Mine ").manifest.name == "Mine"
    assert mgr.clone_bundle(SAMPLE, "t2").manifest.name.endswith("(Cloned)")
    with pytest.raises(ValueError, match="empty"):
        mgr.delete_bundle(" ")
    with pytest.raises(FileNotFoundError):
        mgr.delete_bundle("ghost")
    assert mgr.delete_bundle("t2") is True
    assert not (bundles / "t2").exists()


def test_inspect_bundle_stamps_created_at_from_mtime(tmp_path: Path) -> None:
    d = tmp_path / "b"
    d.mkdir()
    (d / "manifest.json").write_text(
        json.dumps({"id": "b", "name": "B", "version": "1.0.0"}), encoding="utf-8"
    )
    assert BundleManager(storage_dir=tmp_path).inspect_bundle(d).manifest.created_at


# --------------------------------------------------------------------------- CLI


def test_demo_cli_list_inspect_export_clone_runbook(bundles: Path, tmp_path: Path) -> None:
    assert SAMPLE in runner.invoke(app, ["demo", "list"]).stdout
    assert runner.invoke(app, ["demo", "inspect", SAMPLE]).exit_code == 0
    assert runner.invoke(app, ["demo", "inspect", "ghost"]).exit_code == 1
    out = tmp_path / "e.zip"
    assert runner.invoke(app, ["demo", "export", SAMPLE, "--output", str(out)]).exit_code == 0
    assert runner.invoke(app, ["demo", "export", "ghost", "--output", str(out)]).exit_code == 1
    cloned = runner.invoke(app, ["demo", "clone", SAMPLE, "c1", "--name", "C One"])
    assert "Cloned demo bundle" in cloned.stdout
    assert runner.invoke(app, ["demo", "clone", "ghost", "c2"]).exit_code == 1
    assert "Talking Points" in runner.invoke(app, ["demo", "runbook", SAMPLE]).stdout
    assert runner.invoke(app, ["demo", "runbook", "ghost"]).exit_code == 1


def test_demo_cli_verify_stage_branches(bundles: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ok = runner.invoke(app, ["demo", "verify-stage", SAMPLE, "1", "--fake"])
    assert "verified" in ok.stdout
    assert runner.invoke(app, ["demo", "verify-stage", "ghost", "1", "--fake"]).exit_code == 1
    assert runner.invoke(app, ["demo", "verify-stage", SAMPLE, "99", "--fake"]).exit_code == 1
    bare = bundles / "bare"
    bare.mkdir()
    (bare / "manifest.json").write_text(
        json.dumps({"id": "bare", "name": "Bare", "version": "1.0.0"}), encoding="utf-8"
    )
    no_guide = runner.invoke(app, ["demo", "verify-stage", "bare", "1", "--fake"])
    assert no_guide.exit_code == 1
    assert "No walkthrough guide" in no_guide.stdout
    no_inst = runner.invoke(app, ["demo", "verify-stage", SAMPLE, "1", "-i", "nope", "--fake"])
    assert no_inst.exit_code == 1
    assert "Target instance not found" in no_inst.stdout

    async def failing(*_a: object, **_k: object) -> tuple[bool, str]:
        return False, "table empty"

    monkeypatch.setattr(RunbookEngine, "verify_stage", failing)
    live = runner.invoke(app, ["demo", "verify-stage", SAMPLE, "1"])
    assert live.exit_code == 1
    assert "[FAIL] table empty" in live.stdout


def test_demo_cli_seed_rollback_history_flow(bundles: Path) -> None:
    seeded = runner.invoke(app, ["demo", "seed", SAMPLE, "--fake"])
    assert seeded.exit_code == 0
    assert "Table:" in seeded.stdout
    with db_session() as repo:
        op = repo.list_seed_operations()[0]
        repo.update_seed_operation_status(op.id, "rolled_back")
    hist = runner.invoke(app, ["demo", "seed-history"])
    assert "ROLLED_BACK" in hist.stdout
    again = runner.invoke(app, ["demo", "rollback", op.id, "--fake"])
    assert again.exit_code == 1
    assert "already been rolled back" in again.stdout


def test_rollback_demo_prints_errors_from_unreachable_instance() -> None:
    with db_session() as repo:
        repo.add_instance(InstanceCreate(id="dead", name="Dead", url="http://127.0.0.1:1"))
        from now_workbench.db.models import SeedOperationRecord

        repo.record_seed_operation(
            SeedOperationRecord(
                id="op-dead",
                bundle_id="b",
                instance_id="dead",
                created_records=[SeedRecordItem(table="incident", sys_id="s1")],
            )
        )
    res = runner.invoke(app, ["demo", "rollback", "op-dead"])
    assert "Error deleting incident/s1" in res.stdout


def test_doctor_branches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKBENCH_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("PATH", "/bin:/usr/bin")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(settings, "node_bin", "node-does-not-exist-xyz")
    monkeypatch.setattr(settings, "now_sdk_bin", "now-sdk-does-not-exist-xyz")
    monkeypatch.setenv("WORKBENCH_BUNDLES_DIR", str(tmp_path / "new_bundles"))
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0
    assert "Missing" in res.stdout
    assert "Not in PATH" in res.stdout
    assert "Simulation" in res.stdout
    assert "Remediation Recommendations" in res.stdout


def test_doctor_registry_variants(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from now_workbench.db.repository import DatabaseRepository as Repo

    monkeypatch.setattr(Repo, "get_default_instance", lambda self: None)
    res = runner.invoke(app, ["doctor"])
    assert "Instance Registry" in res.stdout
    assert "Active:" not in res.stdout

    def explode(self: Repo) -> str:
        raise RuntimeError("sealed")

    monkeypatch.setattr(Repo, "get_decrypted_anthropic_api_key", explode)
    monkeypatch.delenv("WORKBENCH_ANTHROPIC_API_KEY", raising=False)
    assert "Simulation" in runner.invoke(app, ["doctor"]).stdout
    monkeypatch.setattr(Repo, "get_decrypted_anthropic_api_key", lambda self: "sk-stored")
    assert "Connected" in runner.invoke(app, ["doctor"]).stdout


def test_doctor_fix_installs_sdk_with_stub_npm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub(tmp_path / "bin", "npm", "#!/bin/sh\nexit 0\n")
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}:/bin:/usr/bin")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(settings, "now_sdk_bin", "now-sdk-does-not-exist-xyz")
    res = runner.invoke(app, ["doctor", "--fix", "--mode", "user"])
    assert res.exit_code == 0
    assert "Post-Remediation Verification" in res.stdout
    assert "[OK] ServiceNow SDK" in res.stdout or "ServiceNow SDK" in res.stdout


def test_run_remediation_cli_prints_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_exec(install_mode: str = "user") -> list[RemediationAction]:
        return [
            RemediationAction(component="A", action="x", success=True, details="fine"),
            RemediationAction(component="B", action="y", success=False, details="broke"),
        ]

    monkeypatch.setattr(cli_mod, "execute_remediation", fake_exec)
    cli_mod._run_remediation_cli("user")


def test_backup_to_file_and_stdout(tmp_path: Path) -> None:
    dest = tmp_path / "snap.db"
    res = runner.invoke(app, ["backup", "--out", str(dest)])
    assert res.exit_code == 0
    assert "Backup written" in res.stdout
    assert dest.read_bytes().startswith(b"SQLite format 3")
    piped = runner.invoke(app, ["backup"])
    assert piped.exit_code == 0
    assert piped.stdout_bytes.startswith(b"SQLite format 3")


def test_serve_refuses_unsafe_binding_and_runs_uvicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    import uvicorn

    calls: list[tuple[str, int]] = []

    def fake_run(target: str, host: str, port: int, reload: bool) -> None:
        calls.append((host, port))

    monkeypatch.setattr(uvicorn, "run", fake_run)
    refused = runner.invoke(app, ["serve", "--host", "0.0.0.0", "--port", "9"])
    assert refused.exit_code == 1
    assert calls == []
    ok = runner.invoke(app, ["serve", "--host", "127.0.0.1", "--port", "9"])
    assert ok.exit_code == 0
    assert calls == [("127.0.0.1", 9)]


# --------------------------------------------------------------------------- synthesizer cli


def test_synthesize_and_capture_cli(bundles: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    no_release = runner.invoke(app, ["demo", "synthesize", "Triage incidents"])
    assert no_release.exit_code == 1
    ok = runner.invoke(
        app,
        ["demo", "synthesize", "Triage incidents", "--release", "Zurich", "--id", "syn-1"],
    )
    assert ok.exit_code == 0
    assert (bundles / "syn-1" / "manifest.json").exists()
    fake = runner.invoke(app, ["demo", "capture", "syn-1", "--fake", "--type", "screenshot"])
    assert "Captured screenshot" in fake.stdout
    unknown = runner.invoke(app, ["demo", "capture", "syn-1", "--instance", "nope", "--fake"])
    assert unknown.exit_code == 1
    assert "Instance 'nope' not found" in unknown.stdout
    monkeypatch.setenv("PATH", "/nonexistent-bin")
    failed = runner.invoke(app, ["demo", "capture", "syn-1", "--type", "screenshot"])
    assert failed.exit_code == 1
    assert "Capture failed" in failed.stdout


def test_capture_cli_without_default_instance_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    from now_workbench.db.repository import DatabaseRepository as Repo

    monkeypatch.setattr(Repo, "get_default_instance", lambda self: None)
    res = runner.invoke(app, ["demo", "capture", "x", "--fake"])
    assert res.exit_code == 1
    assert "No default instance registered" in res.stdout


# --------------------------------------------------------------------------- synthesizer engine


def test_synthesize_requires_release_and_avoids_collisions(tmp_path: Path) -> None:
    synth = UseCaseSynthesizer(bundles_dir=tmp_path)
    with pytest.raises(ValueError, match="sn_release"):
        synth.synthesize(UseCaseSynthesisRequest(use_case="x"))
    req = UseCaseSynthesisRequest(
        use_case="Plain persona case",
        sn_release="Zurich",
        bundle_id="same",
        persona_primary="Solo",
        persona_secondary="Duo (Architect)",
    )
    first = synth.synthesize(req, scoped_prefix="X Co!")
    second = synth.synthesize(req)
    assert first.bundle_id == "same"
    assert second.bundle_id == "same-2"
    assert first.fluent_table_name.startswith("xco_same")
    assert "**Solo** (Operations Lead)" in first.narrative_markdown
    assert "**Duo** (Architect)" in first.narrative_markdown
    assert first.sys_properties["glide.ui.polaris.theme.custom_primary"] == "#23a17e"


def test_synthesizer_helpers_fall_back_on_empty_input() -> None:
    from now_workbench.synthesizer import engine as eng

    assert eng._slugify("!!!") == "custom-demo"
    assert eng._table_slug("a b", prefix="!!") == "x_snc_a_b_case"


# --------------------------------------------------------------------------- instances cli


def test_instance_cli_branches() -> None:
    bad = runner.invoke(
        app, ["instance", "add", "N", "fake://n.service-now.com", "--purpose", "zzz"]
    )
    assert bad.exit_code != 0
    ok = runner.invoke(
        app,
        ["instance", "add", "N", "fake://n.service-now.com", "--id", "n1", "--purpose", " TEST "],
    )
    assert ok.exit_code == 0
    assert "detected release" in ok.stdout
    listed = runner.invoke(app, ["instance", "list", "--check"])
    assert "n1" in listed.stdout
    for status, text in (
        ("auth_failed", "Auth Failed"),
        ("unreachable", "Unreachable"),
        ("", "Untested"),
        ("custom", "custom"),
    ):
        rec = cli_mod.format_instance_status.__globals__["InstanceRecord"](
            id="x", name="x", url="u", status=status
        )
        assert text in cli_mod.format_instance_status(rec)
    runner.invoke(
        app, ["instance", "add", "AF", "fake://auth-failed.service-now.com", "--id", "af"]
    )
    runner.invoke(
        app, ["instance", "add", "UR", "fake://unreachable.service-now.com", "--id", "ur"]
    )
    tested = runner.invoke(app, ["instance", "test"])
    assert "[FAIL]" in tested.stdout
    assert "[WARN]" in tested.stdout


# --------------------------------------------------------------------------- remediation


def test_remediation_directories_env_and_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WORKBENCH_BUNDLES_DIR", str(tmp_path / "b"))
    monkeypatch.setenv("WORKBENCH_WORKSPACE_DIR", str(tmp_path / "w"))
    monkeypatch.setenv("WORKBENCH_DATA_DIR", str(tmp_path / "d"))
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text("A=1\n", encoding="utf-8")
    plan = inspect_remediation_needs()
    assert plan.needs_bundles_dir and plan.needs_workspace_dir and plan.needs_env_file
    actions = remediate_directories(plan)
    assert {a.component for a in actions} >= {"Bundles Directory", "Workspaces Directory"}
    assert (tmp_path / "b").is_dir()
    assert remediate_env_file(RemediationPlan()) == []
    assert len(remediate_env_file(plan)) == 1
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "A=1\n"
    (tmp_path / ".env").unlink()
    (tmp_path / ".env.example").unlink()
    other = tmp_path / "other"
    other.mkdir()
    remediate_env_file(plan, target_dir=other)
    assert "now-workbench environment" in (other / ".env").read_text(encoding="utf-8")


async def test_remediate_sdk_outcomes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PATH", "/bin:/usr/bin")
    missing = await remediate_sdk(npm_bin="")
    assert missing.success is False
    assert "npm are required" in missing.details
    ok = tmp_path / "ok"
    _stub(tmp_path, "ok", "#!/bin/sh\nexit 0\n")
    assert (await remediate_sdk(npm_bin=str(ok))).details.startswith(
        "Installed @servicenow/sdk local"
    )
    assert "globally" in (await remediate_sdk(install_mode="global", npm_bin=str(ok))).details
    _stub(tmp_path, "err", "#!/bin/sh\necho nope >&2\nexit 3\n")
    err = await remediate_sdk(npm_bin=str(tmp_path / "err"))
    assert "code 3" in err.details
    assert "nope" in err.details
    _stub(tmp_path, "out", "#!/bin/sh\necho onlyout\nexit 3\n")
    assert "onlyout" in (await remediate_sdk(npm_bin=str(tmp_path / "out"))).details
    _stub(tmp_path, "slow", "#!/bin/sh\nexec sleep 5\n")
    slow = await remediate_sdk(npm_bin=str(tmp_path / "slow"), timeout_seconds=0)
    assert "timed out" in slow.details
    broken = await remediate_sdk(npm_bin=str(tmp_path / "nonexistent"))
    assert "Installation error" in broken.details


async def test_execute_remediation_runs_sdk_step_when_needed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", "/bin:/usr/bin")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("REMEDIATION_TIMEOUT", "5")
    monkeypatch.setattr(settings, "now_sdk_bin", "now-sdk-does-not-exist-xyz")
    results = await execute_remediation()
    assert any(r.component == "ServiceNow SDK" for r in results)
    explicit = await execute_remediation(install_sdk_flag=False, timeout_seconds=1)
    assert all(r.component != "ServiceNow SDK" for r in explicit)


# --------------------------------------------------------------------------- fluent


def test_fluent_parse_diff_and_load(tmp_path: Path) -> None:
    eng = FluentEngine()
    src = (
        "export const t = Table({ name: 'x_t', label: \"T\", schema: {\n"
        "  a: StringColumn({ label: 'A', mandatory: true, maxLength: 40 }),\n"
        "  b: ReferenceColumn({ label: 'B', reference: 'incident' }),\n"
        "  c: StringColumn({ label: 'Tick } x', hint: `a}`, note: 'it\\'s }' }),\n"
        "  d: StringColumn({ label: 'Unclosed' \n"
        "}); Table({ label: 'nameless' });\n"
        "Table({ name: 'broken' "
    )
    schemas = eng.parse_source(src)
    assert [s.name for s in schemas] == ["x_t"]
    cols = {c.name: c for c in schemas[0].columns}
    assert cols["a"].mandatory is True and cols["a"].max_length == 40
    assert cols["b"].reference == "incident" and cols["b"].column_type == "reference"
    assert cols["c"].label == "Tick } x"
    base = eng.parse_source(
        "Table({ name: 'x_t', schema: { a: StringColumn({ label: 'A' }), z: StringColumn({}) } })"
    )
    new = eng.parse_source(
        "Table({ name: 'x_t', schema: { a: ReferenceColumn({ reference: 'user', mandatory: true }),"
        " n: StringColumn({}) } })\nTable({ name: 'x_new', schema: {} })"
    )
    diff = eng.compute_diff(base, new)
    assert diff.added_tables == ["x_new"]
    assert diff.identical is False
    changes = diff.modified_tables["x_t"]
    assert any("type changed" in c for c in changes)
    assert any("reference changed" in c for c in changes)
    assert any("mandatory changed" in c for c in changes)
    assert "Added column 'n' (string)" in changes
    assert "Removed column 'z'" in changes
    removed = eng.compute_diff(new, [])
    assert removed.removed_tables == ["x_new", "x_t"]
    assert eng.compute_diff(base, base).identical is True
    root = tmp_path / "b"
    (root / "fluent").mkdir(parents=True)
    (root / "fluent" / "ok.now.ts").write_text(src, encoding="utf-8")
    (root / "fluent" / "bad.now.ts").write_bytes(b"\xff\xfe")
    assert [s.name for s in eng.load_bundle_schemas(root)] == ["x_t"]
    assert eng.load_bundle_schemas(tmp_path / "missing") == []


# --------------------------------------------------------------------------- chat files

_PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20


def test_detect_media_type_by_content() -> None:
    assert files_mod.detect_media_type(b"%PDF-1.7", "a.bin") == "application/pdf"
    assert files_mod.detect_media_type(_PNG, "a.bin") == "image/png"
    assert files_mod.detect_media_type(b"GIF89a....", "a.bin") == "image/gif"
    assert files_mod.detect_media_type(b"hello", "n.TXT") == "text/plain"
    for data, name in ((b"hello", "n.exe"), (b"a\x00b", "n.txt"), (b"\xff\xfe\xfa", "n.txt")):
        with pytest.raises(files_mod.UnsupportedFileError):
            files_mod.detect_media_type(data, name)


def _thread(created: str) -> ChatThreadRecord:
    return ChatThreadRecord(id="t", title="T", created_at=created)


def _msgs(n: int) -> list[ChatMessageRecord]:
    return [
        ChatMessageRecord(id=f"m{i}", thread_id="t", role="user", content="q") for i in range(n)
    ]


def test_check_can_ask_limits() -> None:
    limits = ConversationLimits(max_turns=2, max_age_days=5)
    now = datetime.now(UTC)
    files_mod.check_can_ask(_thread(now.isoformat()), _msgs(1), limits)
    with pytest.raises(files_mod.LimitReachedError, match="limit of 2 questions"):
        files_mod.check_can_ask(_thread(now.isoformat()), _msgs(2), limits)
    old_naive = (now - timedelta(days=9)).replace(tzinfo=None).isoformat()
    with pytest.raises(files_mod.LimitReachedError, match="older than 5 days"):
        files_mod.check_can_ask(_thread(old_naive), [], limits)


def test_store_read_delete_and_blocks_roundtrip() -> None:
    limits = ConversationLimits()
    pdf = files_mod.store_attachment("t", "dir/Doc.pdf", b"%PDF-1.4 x", [], limits)
    png = files_mod.store_attachment("t", "  ", _PNG, [pdf], limits)
    txt = files_mod.store_attachment("t", "n.md", b"hi", [pdf, png], limits)
    assert pdf.filename == "Doc.pdf"
    assert png.filename == "file"
    assert files_mod.read_bytes(txt) == b"hi"
    blocks = files_mod.claude_blocks([pdf, png, txt])
    assert [b["type"] for b in blocks] == ["document", "image", "document"]
    assert blocks[0]["title"] == "Doc.pdf"
    assert "title" not in blocks[1]
    assert blocks[2]["source"]["data"] == "hi"  # type: ignore[index]
    files_mod.delete_files([pdf, png, txt])
    files_mod.delete_files([pdf])
    with pytest.raises(FileNotFoundError):
        files_mod.read_bytes(pdf)


def test_store_attachment_limit_errors() -> None:
    limits = ConversationLimits(max_file_mb=1, max_files=1, max_conversation_mb=1)
    with pytest.raises(files_mod.UnsupportedFileError, match="empty"):
        files_mod.store_attachment("t", "a.txt", b"", [], limits)
    with pytest.raises(files_mod.LimitReachedError, match="at most 1 MB"):
        files_mod.store_attachment("t", "a.txt", b"x" * (1024 * 1024 + 1), [], limits)
    existing = Attachment(
        id="a", thread_id="t", filename="f", media_type="text/plain", size_bytes=1, created_at="c"
    )
    with pytest.raises(files_mod.LimitReachedError, match="at most 1 files"):
        files_mod.store_attachment("t", "a.txt", b"x", [existing], limits)
    wide = ConversationLimits(max_file_mb=1, max_files=5, max_conversation_mb=1)
    big = existing.model_copy(update={"size_bytes": 1024 * 1024})
    with pytest.raises(files_mod.LimitReachedError, match="total at most 1 MB"):
        files_mod.store_attachment("t", "a.txt", b"x", [big], wide)


# --------------------------------------------------------------------------- seed engine


def _seed_dir(tmp_path: Path, content: str) -> Path:
    (tmp_path / "seed").mkdir()
    (tmp_path / "seed" / "01.json").write_text(content, encoding="utf-8")
    return tmp_path


async def test_seed_engine_resolution_and_payload_errors(tmp_path: Path) -> None:
    repo = _repo()
    eng = SeedEngine(repo, fake_mode=True)
    with pytest.raises(ValueError, match="'zzz' not found"):
        await eng.load_and_seed("b", tmp_path, instance_id="zzz")
    with pytest.raises(ValueError, match="No seed records"):
        await eng.load_and_seed("b", tmp_path)
    with pytest.raises(SeedPayloadError, match="Invalid seed file"):
        await eng.load_and_seed("b", _seed_dir(tmp_path, "{bad"))
    empty = DatabaseRepository(init_db(":memory:"))
    with pytest.raises(ValueError, match="No active default"):
        await SeedEngine(empty, fake_mode=True).load_and_seed("b", tmp_path)


def _handler(request: httpx.Request) -> httpx.Response:
    if request.method == "POST":
        body = json.loads(request.content)
        if body.get("short_description") == "nosys":
            return httpx.Response(201, json={"result": {}})
        return httpx.Response(201, json={"result": {"sys_id": "abc"}})
    if request.method == "GET":
        return httpx.Response(200, json={"result": {"sys_id": "abc"}})
    if "missing" in request.url.path:
        return httpx.Response(404)
    if "refuse" in request.url.path:
        return httpx.Response(500)
    if "explode" in request.url.path:
        raise httpx.ConnectError("down")
    return httpx.Response(204)


async def test_seed_engine_live_post_rollback_and_oauth_paths(tmp_path: Path) -> None:
    repo = _repo()
    repo.add_instance(
        InstanceCreate(id="oa", name="OA", url="https://oa.service-now.com", auth_type="oauth")
    )
    eng = SeedEngine(repo, transport=httpx.MockTransport(_handler))
    root = _seed_dir(
        tmp_path,
        json.dumps(
            [
                {"table": "incident", "fields": {"short_description": "ok"}},
                {"fields": {"short_description": "default table"}},
            ]
        ),
    )
    op = await eng.load_and_seed("b", root, instance_id="oa")
    assert [r.sys_id for r in op.created_records] == ["abc", "abc"]
    verify = await eng.verify(op.id)
    assert all(ok for _r, ok, _d in verify)
    deleted, errors = await eng.rollback(op.id)
    assert (deleted, errors) == (2, [])
    with pytest.raises(ValueError, match="already been rolled back"):
        await eng.rollback(op.id)
    with pytest.raises(ValueError, match="not found"):
        await eng.rollback("zzz")
    bad_root = tmp_path / "bad"
    bad_root.mkdir()
    bad = _seed_dir(
        bad_root, json.dumps([{"table": "incident", "fields": {"short_description": "nosys"}}])
    )
    with pytest.raises(RuntimeError, match="missing sys_id"):
        await eng.load_and_seed("b", bad)


async def test_seed_engine_rollback_collects_failures() -> None:
    repo = _repo()
    from now_workbench.db.models import SeedOperationRecord

    items = [
        SeedRecordItem(table="incident", sys_id="missing"),
        SeedRecordItem(table="incident", sys_id="refuse"),
        SeedRecordItem(table="incident", sys_id="explode"),
    ]
    repo.record_seed_operation(
        SeedOperationRecord(id="op", bundle_id="b", instance_id="inst", created_records=items)
    )
    eng = SeedEngine(repo, transport=httpx.MockTransport(_handler))
    deleted, errors = await eng.rollback("op")
    assert deleted == 1
    assert any("Could not delete incident/refuse" in e for e in errors)
    assert any("Error deleting incident/explode" in e for e in errors)
    assert repo.get_seed_operation("op").status == "rollback_failed"  # type: ignore[union-attr]


# --------------------------------------------------------------------------- remaining branches


def test_cli_version_and_empty_states(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert "now-workbench" in runner.invoke(app, ["version"]).stdout
    empty = tmp_path / "empty"
    monkeypatch.setenv("WORKBENCH_BUNDLES_DIR", str(empty))
    assert "No demonstration bundles found" in runner.invoke(app, ["demo", "list"]).stdout
    assert "No seed operations recorded" in runner.invoke(app, ["demo", "seed-history"]).stdout
    missing = runner.invoke(app, ["demo", "seed", "ghost", "--fake"])
    assert missing.exit_code == 1
    assert "not found" in missing.stdout
    bare = empty / "bare"
    bare.mkdir()
    (bare / "manifest.json").write_text(
        json.dumps({"id": "bare", "name": "Bare", "version": "1.0.0"}), encoding="utf-8"
    )
    assert "No walkthrough guide" in runner.invoke(app, ["demo", "runbook", "bare"]).stdout
    failed = runner.invoke(app, ["demo", "seed", "bare", "--fake"])
    assert failed.exit_code == 1
    assert "Seed operation failed" in failed.stdout


def test_cli_instance_registry_empty_and_default_flags() -> None:
    with db_session() as repo:
        assert repo.delete_instance("default-instance")
    assert "0 registered" in runner.invoke(app, ["doctor"]).stdout
    assert "No instances registered" in runner.invoke(app, ["instance", "list"]).stdout
    added = runner.invoke(
        app, ["instance", "add", "D", "fake://d.service-now.com", "--id", "d1", "--default"]
    )
    assert "Set as active default instance" in added.stdout
    assert runner.invoke(app, ["instance", "test", "d1"]).exit_code == 0


def test_render_remediation_summary_all_sections() -> None:
    cli_mod._render_remediation_summary(RemediationPlan())
    cli_mod._render_remediation_summary(
        RemediationPlan(
            needs_sdk_install=True,
            needs_data_dir=True,
            needs_bundles_dir=True,
            needs_workspace_dir=True,
            needs_env_file=True,
        )
    )


def test_test_demo_cmd_all_stages_pass(bundles: Path) -> None:
    res = runner.invoke(app, ["demo", "test", SAMPLE, "--fake"])
    assert res.exit_code == 0
    assert "stages passed verification" in res.stdout


def test_bundle_manager_list_after_storage_removed(tmp_path: Path) -> None:
    mgr = BundleManager(storage_dir=tmp_path / "gone")
    shutil.rmtree(tmp_path / "gone")
    assert mgr.list_bundles() == []


async def test_full_pipeline_property_and_deploy_failures(
    bundles: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from now_workbench.properties.models import PropertyApplyResult

    with db_session() as repo:
        repo.save_instance_profile(
            InstanceProfile(instance_id="default-instance", release="Zurich")
        )
        inst = repo.get_default_instance()
        assert inst is not None
        engine = DemoPipelineEngine(bundles_dir=bundles, repo=repo)

        async def bad_props(**_kw: object) -> PropertyApplyResult:
            return PropertyApplyResult(success=False, applied_count=0, details=["x failed"])

        monkeypatch.setattr(engine.prop_engine, "apply_bundle_properties", bad_props)
        summary = await engine.run_full_pipeline(SAMPLE, inst, fake_mode=True, record_video=False)
        assert summary.status == "failed"
        assert "x failed" in summary.message
        monkeypatch.undo()
        (bundles / SAMPLE / "package.json").write_text("{}", encoding="utf-8")
        monkeypatch.setattr(pipeline_mod, "NowSdkRunner", _BadRunner)
        deploy = await engine.run_full_pipeline(SAMPLE, inst, fake_mode=True, record_video=False)
        assert deploy.status == "failed"
        assert "SDK deploy failed" in deploy.message


async def test_execute_video_playbook_fake_mode_writes_media(tmp_path: Path) -> None:
    from now_workbench.capture import engine as capture_engine_mod

    video, thumb = tmp_path / "v.webm", tmp_path / "v.png"
    ok, live, steps = await capture_engine_mod._execute_video_playbook(
        tmp_path, "bid", None, "https://x", "", "", video, thumb, 640, 480, fake_mode=True
    )
    assert video.exists()
    assert ok is (video.stat().st_size > 500)
    assert live is False
    assert steps


async def test_run_chrome_capture_success_with_stub_node(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from now_workbench.capture import engine as capture_engine_mod

    _stub(
        tmp_path / "bin",
        "node",
        '#!/bin/sh\nwhile [ $# -gt 0 ]; do [ "$1" = --output ] && out="$2"; shift; done\n'
        'cat >/dev/null\nhead -c 900 /dev/zero > "$out"\nexit 0\n',
    )
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}:/bin:/usr/bin")
    out = tmp_path / "o.png"
    ok, why = await capture_engine_mod._run_chrome_capture("https://x", out, "screenshot", 9, 9)
    assert (ok, why) == (True, "")


def test_migrate_rolls_back_a_failing_migration(monkeypatch: pytest.MonkeyPatch) -> None:
    import sqlite3

    from now_workbench.db import schema as schema_mod

    conn = sqlite3.connect(":memory:", isolation_level=None)
    schema_mod.apply_migrations(conn)
    conn.execute(f"PRAGMA user_version = {schema_mod.SCHEMA_VERSION - 1}")
    broken = (*schema_mod.MIGRATIONS[:-1], "THIS IS NOT SQL;")
    monkeypatch.setattr(schema_mod, "MIGRATIONS", broken)
    with pytest.raises(sqlite3.Error):
        schema_mod.apply_migrations(conn)
    assert not conn.in_transaction
    assert conn.execute("PRAGMA user_version").fetchone()[0] == schema_mod.SCHEMA_VERSION - 1
    conn.close()


async def test_seed_engine_rejected_post_and_fake_rollback(tmp_path: Path) -> None:
    repo = _repo()

    def reject(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server says no")

    root = _seed_dir(tmp_path, json.dumps([{"table": "incident", "fields": {"a": "b"}}]))
    eng = SeedEngine(repo, transport=httpx.MockTransport(reject))
    with pytest.raises(RuntimeError, match="HTTP 500 - server says no"):
        await eng.load_and_seed("b", root)
    fake = SeedEngine(repo, fake_mode=True)
    op = await fake.load_and_seed("b", root)
    assert await fake.rollback(op.id) == (1, [])


def test_fluent_parse_skips_column_with_unterminated_string() -> None:
    src = (
        "Table({ name: 'x_u', schema: { ok: StringColumn({ label: 'O' }), "
        "bad: StringColumn({ label: 'x }) } })"
    )
    schemas = FluentEngine().parse_source(src)
    assert [c.name for c in schemas[0].columns] == ["ok"]


def test_instance_cli_activate_rename_delete_test_flows() -> None:
    runner.invoke(app, ["instance", "add", "N", "fake://n.service-now.com", "--id", "n1"])
    assert "now ACTIVE" in runner.invoke(app, ["instance", "activate", "n1"]).stdout
    assert runner.invoke(app, ["instance", "activate", "zz"]).exit_code == 1
    assert "renamed to" in runner.invoke(app, ["instance", "rename", "n1", "M"]).stdout
    assert runner.invoke(app, ["instance", "rename", "zz", "M"]).exit_code == 1
    assert "Authenticated as" in runner.invoke(app, ["instance", "test", "n1"]).stdout
    assert runner.invoke(app, ["instance", "test", "zz"]).exit_code == 1
    assert "deleted" in runner.invoke(app, ["instance", "delete", "n1"]).stdout
    assert runner.invoke(app, ["instance", "delete", "n1"]).exit_code == 1


async def test_capture_screenshot_success_is_labelled_native(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from now_workbench.capture.engine import PlaywrightCaptureEngine
    from now_workbench.capture.models import CaptureRequest

    _stub(
        tmp_path / "bin",
        "node",
        '#!/bin/sh\nwhile [ $# -gt 0 ]; do [ "$1" = --output ] && out="$2"; shift; done\n'
        'cat >/dev/null\nhead -c 900 /dev/zero > "$out"\nexit 0\n',
    )
    monkeypatch.setenv("PATH", f"{tmp_path / 'bin'}:/bin:/usr/bin")
    eng = PlaywrightCaptureEngine(bundles_dir=tmp_path / "b")
    req = CaptureRequest(bundle_id="x", target_path="/p", media_type="screenshot")
    art = await eng.capture(req, instance_url="https://i.service-now.com")
    assert art.engine == "google-chrome-native"
    assert eng.list_captures("x")[0].id == art.id


def test_cli_module_runs_as_main(monkeypatch: pytest.MonkeyPatch) -> None:
    import runpy
    import sys

    monkeypatch.setattr(sys, "argv", ["workbench", "--help"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(REPO_ROOT / "src" / "now_workbench" / "cli.py"), run_name="__main__")
    assert exc.value.code == 0


def test_instance_cli_test_with_empty_registry_exits_1() -> None:
    with db_session() as repo:
        assert repo.delete_instance("default-instance")
    res = runner.invoke(app, ["instance", "test"])
    assert res.exit_code == 1
    assert "No instance found to test" in res.stdout
