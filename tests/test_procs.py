# tests/test_procs.py
# Bounded child processes: deadlines, whole-group stop, no zombies.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for now_workbench.procs (resource management)."""

import asyncio
import os
from pathlib import Path

import pytest

from now_workbench.procs import ProcessTimeoutError, communicate_bounded, spawn, stop
from now_workbench.sdk.runner import NowSdkRunner


async def test_communicate_bounded_returns_output_with_stdin(tmp_path: Path) -> None:
    """A command that finishes in time returns its output; stdin reaches it."""
    proc = await spawn(["cat"], stdin=True, cwd=tmp_path, env=dict(os.environ))
    out, err = await communicate_bounded(proc, 10, b"hello")
    assert out == b"hello" and err == b""


async def test_communicate_bounded_stops_the_whole_group_on_timeout(tmp_path: Path) -> None:
    """On timeout the command and the children it started are stopped and reaped."""
    marker = tmp_path / "child.pid"
    proc = await spawn(["sh", "-c", f"sleep 30 & echo $! > {marker}; wait"], merge_stderr=True)
    with pytest.raises(ProcessTimeoutError, match="stopped after"):
        await communicate_bounded(proc, 0.5)
    assert proc.returncode is not None
    child = int(marker.read_text().strip())
    await asyncio.sleep(0.1)
    with pytest.raises(ProcessLookupError):
        os.kill(child, 0)


async def test_stop_escalates_when_the_process_ignores_terminate() -> None:
    """A process that traps SIGTERM is killed after the grace period."""
    from now_workbench import procs

    proc = await spawn(["sh", "-c", "trap '' TERM; sleep 30"])
    await asyncio.sleep(0.2)
    original = procs._GRACE_S
    procs._GRACE_S = 0.3
    try:
        await stop(proc)
    finally:
        procs._GRACE_S = original
    assert proc.returncode is not None
    await stop(proc)  # stopping a finished process is a no-op


async def test_run_command_times_out_and_reports_it(tmp_path: Path) -> None:
    """A stuck now-sdk command is stopped with exit code 124 and a clear message."""
    script = tmp_path / "now-sdk"
    script.write_text("#!/bin/sh\necho started\nsleep 30\n", encoding="utf-8")
    script.chmod(0o755)
    runner = NowSdkRunner(now_sdk_bin=str(script), timeout_s=0.5)
    res = await runner.run_command(["build"], cwd=tmp_path)
    assert res.success is False and res.exit_code == 124
    assert "stopped after" in res.output and "started" in res.output


async def test_run_chrome_capture_reports_a_stuck_browser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A capture that outlives its deadline is stopped and reported, not waited on forever."""
    from now_workbench.capture import engine

    fake_node = tmp_path / "node"
    fake_node.write_text("#!/bin/sh\nsleep 30\n", encoding="utf-8")
    fake_node.chmod(0o755)
    monkeypatch.setattr(engine.shutil, "which", lambda _name: str(fake_node))
    monkeypatch.setattr(engine, "_CAPTURE_TIMEOUT_S", 0.3)
    ok, why = await engine._run_chrome_capture(
        "https://x.service-now.com", tmp_path / "shot.png", "image", 800, 600
    )
    assert not ok and why.startswith("the browser stopped after")


async def test_run_runner_reports_a_stuck_playbook(monkeypatch: pytest.MonkeyPatch) -> None:
    """A walkthrough that outlives its deadline is stopped and reported."""
    from now_workbench.capture import driver
    from now_workbench.db.models import InstanceRecord

    monkeypatch.setattr(driver, "_PLAYBOOK_TIMEOUT_S", 0.3)
    inst = InstanceRecord(id="i", name="I", url="https://x.service-now.com")
    error = await driver._run_runner(["sh", "-c", "sleep 30"], inst)
    assert error is not None and error.startswith("playbook runner stopped after")


async def test_otto_client_aclose_closes_only_the_pool_it_created() -> None:
    """A client built from a key is closed; a client handed in is left to its owner."""
    from now_workbench.ai.client import OttoClient

    owned = OttoClient(api_key="sk-ant-x")
    await owned.aclose()
    assert owned.client.is_closed()

    class _Borrowed:
        closed = False

        async def close(self) -> None:
            self.closed = True

    borrowed = _Borrowed()
    await OttoClient(api_key="sk-ant-x", client=borrowed).aclose()
    assert not borrowed.closed
