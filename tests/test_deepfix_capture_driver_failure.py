# tests/test_deepfix_capture_driver_failure.py
# Regression tests: a failed playbook runner must never be reported as passing
# Author: Pierre Grothe
# Date: 2026-11-06
"""A crashed or log-less playbook runner is reported as a failure, not a pass."""

from pathlib import Path

import pytest

from now_workbench.capture import driver as driver_mod
from now_workbench.capture.driver import PlaywrightPlaybookDriver
from now_workbench.capture.playbook import DemoPlaybook, PlaybookActionType, PlaybookStep
from now_workbench.db.models import InstanceRecord


def _playbook() -> DemoPlaybook:
    return DemoPlaybook(
        bundle_id="b",
        title="T",
        steps=[
            PlaybookStep(id="s1", action=PlaybookActionType.AUTHENTICATE, description="a"),
            PlaybookStep(id="s2", action=PlaybookActionType.NAVIGATE, description="n", path="/x"),
        ],
    )


def _instance() -> InstanceRecord:
    return InstanceRecord(
        id="i",
        name="I",
        url="https://x.service-now.com",
        username="admin",
        password="pwd",
        auth_type="basic",
        release="Xanadu",
        is_default=True,
    )


async def test_execute_playbook_runner_nonzero_exit_reports_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_run(cmd: list[str], instance: InstanceRecord) -> str | None:
        return "playbook runner exited with code 1: boom"

    monkeypatch.setattr(driver_mod, "_run_runner", fake_run)
    drv = PlaywrightPlaybookDriver(data_dir=tmp_path / "data")
    (tmp_path / "m").mkdir()
    res = await drv.execute_playbook(
        _playbook(), _instance(), tmp_path / "m" / "p.webm", tmp_path / "m" / "p.png"
    )
    assert res.success is False
    assert res.passed_steps == 0
    assert all(s.status != "passed" for s in res.step_results)
    assert "code 1: boom" in (res.step_results[0].error_message or "")


async def test_run_runner_missing_executable_returns_error(tmp_path: Path) -> None:
    err = await driver_mod._run_runner([str(tmp_path / "does-not-exist")], _instance())
    assert err is not None
    assert "could not be started" in err


async def test_run_runner_nonzero_exit_includes_stderr_tail(tmp_path: Path) -> None:
    script = tmp_path / "fail.sh"
    script.write_text("#!/bin/sh\necho oops-detail 1>&2\nexit 3\n")
    script.chmod(0o755)
    err = await driver_mod._run_runner([str(script)], _instance())
    assert err is not None
    assert "code 3" in err
    assert "oops-detail" in err
