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
from now_workbench.domains.capture.playbook import DemoPlaybook, PlaybookExecutionResult
from now_workbench.domains.instances import InstanceCreate, InstanceRepository
from now_workbench.domains.instances.models import InstanceProfile
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
    """The capture engine and its callers carry no hard-coded release."""
    for rel in (
        "domains/capture/engine.py",
        "interfaces/api/captures.py",
        "interfaces/ai/tools/demos.py",
    ):
        text = (REPO / "src" / "now_workbench" / rel).read_text(encoding="utf-8")
        assert "Xanadu" not in text, rel


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


def test_api_capture_on_undetected_instance_is_502_naming_the_gap() -> None:
    """The endpoint reports the unknown release instead of capturing a guessed path."""
    _instance("nodetect", None)
    res = TestClient(create_app()).post(
        f"/api/demos/{BUNDLE}/captures", json={"bundle_id": BUNDLE, "instance_id": "nodetect"}
    )
    assert res.status_code == 502
    assert "release is unknown" in res.json()["detail"]


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


def test_chrome_capture_script_reads_settle_ms() -> None:
    """The Node script parses ``--settle-ms`` and waits that long before the shot."""
    script = (REPO / "scripts" / "dev-tools" / "chrome_capture.mjs").read_text(encoding="utf-8")
    assert '"--settle-ms"' in script
    assert "opts.settleMs" in script
