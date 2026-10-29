"""Tests for NowSdkRunner."""

import pytest
from pathlib import Path
from now_workbench.sdk.runner import NowSdkRunner


@pytest.mark.asyncio
async def test_runner_fake_mode(tmp_path: Path) -> None:
    runner = NowSdkRunner(fake_mode=True)
    probe = runner.probe_environment()
    assert probe["node_available"] is True
    assert probe["now_sdk_available"] is True

    logs: list[str] = []

    async def log_sink(line: str) -> None:
        logs.append(line)

    res = await runner.build(tmp_path, stream_callback=log_sink)
    assert res.success is True
    assert res.exit_code == 0
    assert len(logs) > 0
    assert "build" in res.command
