# tests/test_capture_detected_release.py
# Captures translate paths for the instance's detected release, never a default (STORY-074).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests that every capture path uses the detected release and refuses an unknown one.

No test contacts a network or starts a browser: the browser run, the playbook driver and the
capture engine are replaced by in-memory recorders, and the Node binary is a shell stub.
"""

import inspect
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from now_workbench.domains.capture import CaptureFailedError, CaptureRequest
from now_workbench.domains.capture import engine as capture_engine_mod
from now_workbench.domains.capture.driver import PlaywrightPlaybookDriver
from now_workbench.domains.capture.engine import PlaywrightCaptureEngine
from now_workbench.domains.capture.models import Viewport
from now_workbench.domains.capture.playbook import (
    DemoPlaybook,
    PlaybookExecutionResult,
    PlaybookStep,
)
from now_workbench.domains.demos.pipeline import DemoPipelineEngine
from now_workbench.domains.instances import InstanceCreate, InstanceRecord, InstanceRepository
from now_workbench.domains.instances.models import InstanceProfile
from now_workbench.domains.settings import PreferencesRepository
from now_workbench.domains.settings.models import (
    WorkbenchPreferences,
    WorkbenchPreferencesUpdate,
)
from now_workbench.interfaces.ai.tools.base import ToolContext, execute_tool
from now_workbench.interfaces.api.app import create_app
from now_workbench.interfaces.cli.main import app as cli_app
from now_workbench.platform.db.session import db_session

REPO = Path(__file__).resolve().parents[1]
BUNDLE = "sample-ai-assistant"
CLASSIC = "/now/nav/ui/classic/params/target/incident_list.do"


def _instance(inst_id: str, release: str | None) -> None:
    """Register a live-looking instance whose detected profile carries ``release``."""
    with db_session() as conn:
        repo = InstanceRepository(conn)
        repo.add_instance(
            InstanceCreate(
                id=inst_id, name=inst_id, url=f"https://{inst_id}.service-now.com", password="p"
            )
        )
        if release is not None:
            repo.save_instance_profile(InstanceProfile(instance_id=inst_id, release=release))


def _record_release(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """Replace the capture engine with a recorder of the release it was handed."""
    seen: list[object] = []

    async def capture(self: object, req: CaptureRequest, **kwargs: object) -> None:
        seen.append(kwargs.get("release", "<not passed>"))
        raise CaptureFailedError("recorded")

    monkeypatch.setattr(PlaywrightCaptureEngine, "capture", capture)
    return seen


def _record_shots(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Replace the live browser run with a recorder that writes a real-sized file."""
    calls: list[dict[str, Any]] = []

    async def run(full_url: str, output_file: Path, *_a: object, **kw: Any) -> tuple[bool, str]:
        calls.append({"url": full_url, **kw})
        output_file.write_bytes(b"\x89PNG" + b"0" * 600)
        return True, ""

    monkeypatch.setattr(capture_engine_mod, "_run_chrome_capture", run)
    return calls


# -- AC1: no Xanadu default, anywhere ----------------------------------------------------------


def test_capture_release_has_no_default() -> None:
    """``capture`` cannot be called without the instance's release."""
    param = inspect.signature(PlaywrightCaptureEngine.capture).parameters["release"]
    assert param.default is inspect.Parameter.empty


def test_no_capture_code_path_names_xanadu() -> None:
    """The capture engine and every caller carry no hard-coded release.

    A bundle's ``min_release`` default in the pipeline is a requirement, not the instance's
    release, so that one line is allowed.
    """
    for rel in (
        "domains/capture/engine.py",
        "domains/demos/pipeline.py",
        "interfaces/api/captures.py",
        "interfaces/ai/tools/demos.py",
        "interfaces/cli/synthesizer.py",
    ):
        text = (REPO / "src" / "now_workbench" / rel).read_text(encoding="utf-8")
        named = [n for n in text.splitlines() if "Xanadu" in n and "min_release" not in n]
        assert named == [], rel


async def test_pipeline_video_proof_passes_the_instance_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``record_video_proof`` hands the engine the instance's own release, nothing else."""
    seen: list[object] = []

    async def capture(self: object, req: CaptureRequest, **kwargs: object) -> None:
        seen.append(kwargs.get("release", "<not passed>"))
        raise CaptureFailedError("recorded")

    monkeypatch.setattr(PlaywrightCaptureEngine, "capture", capture)
    inst = InstanceRecord(id="r", name="R", url="https://r.service-now.com", release="Rome")
    with db_session(tmp_path / "t.db") as conn:
        engine = DemoPipelineEngine(bundles_dir=REPO / "bundles", conn=conn)
        with pytest.raises(CaptureFailedError):
            await engine.record_video_proof(BUNDLE, inst, fake_mode=False)
    assert seen == ["Rome"]


@pytest.mark.parametrize(
    ("path", "release", "expected"),
    [
        (
            "now/nav/ui/classic/params/target/incident_list.do",
            "Rome",
            "/nav_to.do?uri=incident_list.do",
        ),
        ("now/sow/home", "Rome", "/now/workspace/agent/home"),
        ("/now/sow/home", "Rome", "/now/workspace/agent/home"),
        ("//now/sow/home", "Australia", "/now/sow/home"),
        ("incident_list.do", "Australia", "/incident_list.do"),
        ("@workspace/itsm/x", "Australia", "/now/sow/x"),
        ("/@workspace/itsm/x", "Australia", "/now/sow/x"),
        ("/@workspace/itsm/x", "Rome", "/now/workspace/agent/x"),
        ("https://other.service-now.com/a.do", "Australia", "https://other.service-now.com/a.do"),
        ("now/sow/home", "Unknown", "/now/sow/home"),
        ("/@workspace/itsm/x", "", "/@workspace/itsm/x"),
    ],
)
def test_paths_get_exactly_one_leading_slash_before_translation(
    path: str, release: str, expected: str
) -> None:
    """Slash-less and slashed paths translate alike; full URLs keep their form."""
    assert capture_engine_mod._translate(path, release) == expected


async def test_screenshot_translates_a_slash_less_legacy_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A slash-less classic path still gets the legacy form on a pre-San Diego release."""
    calls = _record_shots(monkeypatch)
    eng = PlaywrightCaptureEngine(bundles_dir=tmp_path)
    req = CaptureRequest(bundle_id="b", target_path=CLASSIC.lstrip("/"))
    art = await eng.capture(req, instance_url="https://x", release="Rome")
    assert art.target_path == "/nav_to.do?uri=incident_list.do"
    assert calls[0]["url"] == "https://x/nav_to.do?uri=incident_list.do"


def test_playbook_step_paths_are_normalised_and_urls_kept() -> None:
    """Step paths get one leading slash; a step on a full URL is left as written."""
    playbook = DemoPlaybook(
        bundle_id="b",
        title="t",
        start_path="/@workspace/itsm/home",
        steps=[
            PlaybookStep(id="a", action="navigate", description="a", path="now/sow/list"),
            PlaybookStep(id="b", action="navigate", description="b", path="https://y/z.do"),
        ],
    )
    out = capture_engine_mod._translated_playbook(playbook, "Rome")
    assert out.start_path == "/now/workspace/agent/home"
    assert [s.path for s in out.steps] == ["/now/workspace/agent/list", "https://y/z.do"]


async def test_screenshot_translates_for_the_given_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-San Diego release gets the legacy path; a current one keeps Next Experience."""
    calls = _record_shots(monkeypatch)
    eng = PlaywrightCaptureEngine(bundles_dir=tmp_path)
    req = CaptureRequest(bundle_id="b", target_path=CLASSIC)
    old = await eng.capture(req, instance_url="https://x", release="Rome")
    new = await eng.capture(req, instance_url="https://x", release="Australia")
    assert old.target_path == "/nav_to.do?uri=incident_list.do"
    assert new.target_path == CLASSIC
    assert [c["url"] for c in calls] == [f"https://x{old.target_path}", f"https://x{CLASSIC}"]


def test_api_capture_passes_the_detected_release(monkeypatch: pytest.MonkeyPatch) -> None:
    """The capture endpoint hands the engine the instance's detected release."""
    _instance("rome", "Rome")
    seen = _record_release(monkeypatch)
    res = TestClient(create_app()).post(
        f"/api/demos/{BUNDLE}/captures", json={"bundle_id": BUNDLE, "instance_id": "rome"}
    )
    assert res.status_code == 502
    assert seen == ["Rome"]


def test_otto_capture_passes_the_detected_release(monkeypatch: pytest.MonkeyPatch) -> None:
    """Otto's capture tool hands the engine the instance's detected release."""
    _instance("rome", "Rome")
    seen = _record_release(monkeypatch)
    with db_session() as conn:
        execute_tool(
            ToolContext(conn=conn), "capture_media", {"bundle_id": BUNDLE, "instance": "rome"}
        )
    assert seen == ["Rome"]


def test_cli_capture_passes_the_detected_release(monkeypatch: pytest.MonkeyPatch) -> None:
    """``demo capture`` hands the engine the instance's detected release."""
    _instance("rome", "Rome")
    seen = _record_release(monkeypatch)
    res = CliRunner().invoke(cli_app, ["demo", "capture", BUNDLE, "--instance", "rome"])
    assert res.exit_code == 1
    assert seen == ["Rome"]


def _record_playbooks(monkeypatch: pytest.MonkeyPatch) -> list[tuple[DemoPlaybook, str]]:
    """Replace the playbook driver with a recorder of the playbook and the instance release."""
    seen: list[tuple[DemoPlaybook, str]] = []

    async def execute(
        self: object, playbook: DemoPlaybook, instance: Any, output_video: Path, **_k: object
    ) -> PlaybookExecutionResult:
        seen.append((playbook, instance.release))
        output_video.write_bytes(b"\x1a\x45\xdf\xa3" + b"0" * 600)
        return PlaybookExecutionResult(
            bundle_id=playbook.bundle_id,
            playbook_title=playbook.title,
            success=True,
            total_steps=0,
            passed_steps=0,
        )

    monkeypatch.setattr(PlaywrightPlaybookDriver, "execute_playbook", execute)
    return seen


def _bundle_with_playbook(root: Path) -> None:
    walk = root / "b" / "walkthrough"
    walk.mkdir(parents=True)
    playbook = {
        "bundle_id": "b",
        "title": "Walk",
        "start_path": "@workspace/itsm/home",
        "steps": [
            {"id": "s1", "action": "navigate", "description": "go", "path": "@workspace/itsm/x"},
            {"id": "s2", "action": "click", "description": "c", "selector": "#a"},
        ],
    }
    (walk / "playbook.json").write_text(json.dumps(playbook), encoding="utf-8")


async def test_video_walkthrough_uses_the_release_and_records_its_real_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A video signs in with the detected release, translates the playbook's paths for it,
    and records the path it actually opened (the playbook start), not ``target_path``."""
    _bundle_with_playbook(tmp_path)
    seen = _record_playbooks(monkeypatch)
    monkeypatch.setattr(PlaywrightPlaybookDriver, "__init__", lambda self, data_dir=None: None)
    eng = PlaywrightCaptureEngine(bundles_dir=tmp_path)
    req = CaptureRequest(bundle_id="b", target_path="/ignored.do", media_type="video")
    art = await eng.capture(req, instance_url="https://x", release="Rome")
    playbook, release = seen[0]
    assert release == "Rome"
    assert playbook.start_path == "/now/workspace/agent/home"
    assert playbook.steps[0].path == "/now/workspace/agent/x"
    assert playbook.steps[1].path is None
    assert art.target_path == "/now/workspace/agent/home"


async def test_fake_video_records_the_playbook_start(tmp_path: Path) -> None:
    """A simulated video stands in for the walkthrough, so it records the playbook's start."""
    _bundle_with_playbook(tmp_path)
    eng = PlaywrightCaptureEngine(bundles_dir=tmp_path)
    req = CaptureRequest(
        bundle_id="b", target_path="/ignored.do", media_type="video", fake_mode=True
    )
    art = await eng.capture(req, instance_url="https://x", release="Australia")
    assert art.target_path == "/now/sow/home"


# -- AC2: an unknown release is said, not guessed ----------------------------------------------


@pytest.mark.parametrize("release", ["Unknown", "", "  "])
@pytest.mark.parametrize("media_type", ["screenshot", "video"])
async def test_live_capture_refuses_an_unknown_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, release: str, media_type: str
) -> None:
    """A live capture with no detected release says so and starts no browser."""
    calls = _record_shots(monkeypatch)
    played = _record_playbooks(monkeypatch)
    eng = PlaywrightCaptureEngine(bundles_dir=tmp_path)
    req = CaptureRequest(bundle_id="b", target_path=CLASSIC, media_type=media_type)
    with pytest.raises(CaptureFailedError, match="release is unknown.*connection test"):
        await eng.capture(req, instance_url="https://x", release=release)
    assert calls == [] and played == []
    assert eng.list_captures("b") == []


async def test_simulated_capture_with_unknown_release_keeps_the_path_untranslated(
    tmp_path: Path,
) -> None:
    """A placeholder needs no release; its record keeps the requested path, not a guess."""
    eng = PlaywrightCaptureEngine(bundles_dir=tmp_path)
    req = CaptureRequest(bundle_id="b", target_path=CLASSIC, fake_mode=True)
    art = await eng.capture(req, instance_url="https://x", release="Unknown")
    assert art.engine == "playwright-simulated"
    assert art.target_path == CLASSIC


def test_api_capture_on_undetected_instance_is_409_naming_the_gap() -> None:
    """The endpoint reports the unknown release (a fixable precondition) instead of guessing."""
    _instance("nodetect", None)
    res = TestClient(create_app()).post(
        f"/api/demos/{BUNDLE}/captures", json={"bundle_id": BUNDLE, "instance_id": "nodetect"}
    )
    assert res.status_code == 409
    assert "release is unknown" in res.json()["detail"]
    assert "connection test" in res.json()["detail"]


# -- wait_timeout_ms is the screenshot's page settle -------------------------------------------


async def test_capture_hands_the_settle_wait_to_the_browser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``wait_timeout_ms`` reaches the screenshot run."""
    calls = _record_shots(monkeypatch)
    eng = PlaywrightCaptureEngine(bundles_dir=tmp_path)
    await eng.capture(
        CaptureRequest(bundle_id="b"),
        instance_url="https://x",
        release="Zurich",
        wait_timeout_ms=2500,
    )
    assert calls[0]["settle_ms"] == 2500


async def test_run_chrome_capture_passes_settle_ms_to_node(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The settle wait is a ``--settle-ms`` argument of the capture script."""
    argv_file = tmp_path / "argv.txt"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    node = bin_dir / "node"
    node.write_text(f'#!/bin/sh\ncat >/dev/null\necho "$@" > {argv_file}\nexit 3\n', "utf-8")
    node.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:/bin:/usr/bin")
    ok, _why = await capture_engine_mod._run_chrome_capture(
        "https://x", tmp_path / "o.png", "screenshot", Viewport(width=10, height=10), settle_ms=2500
    )
    assert ok is False
    assert "--settle-ms 2500" in argv_file.read_text(encoding="utf-8")


def _parse_capture_args(*argv: str) -> dict[str, Any]:
    """Run ``chrome_capture.mjs``'s own argument parser in Node and return its options."""
    node = shutil.which("node")
    assert node, "node is required (the Fluent SDK and the drivers run on it)"
    script_uri = (REPO / "scripts" / "dev-tools" / "chrome_capture.mjs").as_uri()
    script = (
        f"import {{ parseArgs }} from {json.dumps(script_uri)};"
        f"process.stdout.write(JSON.stringify(parseArgs({json.dumps(list(argv))})));"
    )
    done = subprocess.run(
        [node, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    parsed: dict[str, Any] = json.loads(done.stdout)
    return parsed


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        ((), 1500),
        (("--settle-ms", "2500"), 2500),
        (("--settle-ms", "0"), 0),
        (("--settle-ms", "-5"), 0),
        (("--settle-ms", "99999"), 30000),
        (("--settle-ms", "soon"), 1500),
    ],
)
def test_chrome_capture_parses_and_clamps_settle_ms(argv: tuple[str, ...], expected: int) -> None:
    """``--settle-ms`` is parsed, clamped to 0..30000 and defaults to 1500."""
    assert _parse_capture_args("--url", "https://x", *argv)["settleMs"] == expected


def test_chrome_capture_waits_the_parsed_settle_not_a_fixed_delay() -> None:
    """The page settle before the shot is the parsed value; no fixed 600 ms wait remains."""
    script = (REPO / "scripts" / "dev-tools" / "chrome_capture.mjs").read_text(encoding="utf-8")
    assert "setTimeout(r, opts.settleMs)" in script
    assert "setTimeout(r, 600)" not in script and "settleMs: 600" not in script


def test_wait_timeout_preference_is_bounded_to_the_script_range() -> None:
    """``capture_wait_timeout_ms`` accepts 0..30000 and defaults to 1500."""
    assert WorkbenchPreferences().capture_wait_timeout_ms == 1500
    for bad in (-1, 30001):
        with pytest.raises(ValueError, match="capture_wait_timeout_ms"):
            WorkbenchPreferences(capture_wait_timeout_ms=bad)
        with pytest.raises(ValueError, match="capture_wait_timeout_ms"):
            WorkbenchPreferencesUpdate(capture_wait_timeout_ms=bad)
    assert WorkbenchPreferences(capture_wait_timeout_ms=30000).capture_wait_timeout_ms == 30000
    assert WorkbenchPreferencesUpdate(capture_wait_timeout_ms=0).capture_wait_timeout_ms == 0


def test_cli_capture_uses_the_wait_preference(monkeypatch: pytest.MonkeyPatch) -> None:
    """``demo capture`` hands the engine the ``capture_wait_timeout_ms`` preference."""
    seen: list[object] = []

    async def capture(self: object, req: CaptureRequest, **kwargs: object) -> None:
        seen.append(kwargs.get("wait_timeout_ms", "<not passed>"))
        raise CaptureFailedError("recorded")

    monkeypatch.setattr(PlaywrightCaptureEngine, "capture", capture)
    with db_session() as conn:
        PreferencesRepository(conn).update_workbench_preferences(
            WorkbenchPreferencesUpdate(capture_wait_timeout_ms=4200)
        )
    res = CliRunner().invoke(cli_app, ["demo", "capture", BUNDLE])
    assert res.exit_code == 1
    assert seen == [4200]
