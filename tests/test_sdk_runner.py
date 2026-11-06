"""Tests for NowSdkRunner."""

from pathlib import Path

import pytest

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

    deploy_res = await runner.deploy(
        tmp_path,
        stream_callback=log_sink,
        instance_url="https://demo-test.service-now.com",
        username="admin",
        password="pwd",
    )
    assert deploy_res.success is True
    assert "deploy" in deploy_res.command
    assert any("demo-test.service-now.com" in line for line in logs)


@pytest.mark.asyncio
async def test_runner_subprocess_execution(tmp_path: Path) -> None:
    """Verify real async subprocess execution, exit code checking, and log streaming."""
    runner = NowSdkRunner(now_sdk_bin="echo", fake_mode=False)
    captured: list[str] = []

    async def log_sink(line: str) -> None:
        captured.append(line)

    res = await runner.run_command(
        ["hello", "fluent", "sdk"], cwd=tmp_path, stream_callback=log_sink
    )
    assert res.success is True
    assert res.exit_code == 0
    assert "hello fluent sdk" in res.output
    assert any("hello fluent sdk" in line for line in captured)

    # Real command failure
    fail_runner = NowSdkRunner(now_sdk_bin="false", fake_mode=False)
    fail_res = await fail_runner.run_command([], cwd=tmp_path)
    assert fail_res.success is False
    assert fail_res.exit_code != 0

    # Binary missing failure with callback
    missing_logs: list[str] = []

    async def missing_cb(line: str) -> None:
        missing_logs.append(line)

    missing_runner = NowSdkRunner(
        now_sdk_bin="nonexistent-now-sdk-runner",
        sdk_candidates=(),
        user_local_dir=tmp_path / "empty",
        fake_mode=False,
    )
    missing_res = await missing_runner.run_command(
        ["build"], cwd=tmp_path, stream_callback=missing_cb
    )
    assert missing_res.success is False
    assert missing_res.exit_code == 127
    assert len(missing_logs) > 0


def test_runner_binary_resolution(tmp_path: Path) -> None:
    """Verify now-sdk binary discovery across PATH and fallbacks."""
    runner = NowSdkRunner(now_sdk_bin="python3")
    resolved = runner.resolve_sdk_bin()
    assert resolved is not None
    assert "python" in resolved

    # Fallback to candidate list
    candidate_runner = NowSdkRunner(now_sdk_bin="nonexistent-bin-12345", sdk_candidates=("sh",))
    assert candidate_runner.resolve_sdk_bin() is not None

    # Fallback to user-local .bin directory
    local_dir = tmp_path / "custom_sdk" / ".bin"
    local_dir.mkdir(parents=True, exist_ok=True)
    dummy_bin = local_dir / "custom-now-sdk-test"
    dummy_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    dummy_bin.chmod(0o755)

    local_runner = NowSdkRunner(
        now_sdk_bin="custom-now-sdk-test",
        sdk_candidates=(),
        user_local_dir=local_dir,
    )
    assert local_runner.resolve_sdk_bin() == str(dummy_bin)

    # None resolved
    missing_runner = NowSdkRunner(
        now_sdk_bin="nonexistent-bin-99999",
        node_bin="nonexistent-node-99999",
        sdk_candidates=(),
        user_local_dir=tmp_path / "empty_bin",
    )
    assert missing_runner.resolve_sdk_bin() is None
    missing_probe = missing_runner.probe_environment()
    assert missing_probe["node_available"] is False
    assert missing_probe["now_sdk_available"] is False


@pytest.mark.asyncio
async def test_deploy_passes_credentials_in_the_sdk_ci_environment(tmp_path: Path) -> None:
    """now-sdk gets the instance and account through its CI variables, never as arguments."""
    script = tmp_path / "now-sdk"
    script.write_text(
        '#!/bin/sh\necho "args=$*"\necho "mode=$SN_SDK_NODE_ENV type=$SN_SDK_AUTH_TYPE"\n'
        'echo "url=$SN_SDK_INSTANCE_URL user=$SN_SDK_USER pwd_set=${SN_SDK_USER_PWD:+yes}"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    res = await NowSdkRunner(now_sdk_bin=str(script)).deploy(
        tmp_path, instance_url="https://dev.service-now.com", username="admin", password="s3cret"
    )
    assert res.success is True
    assert "args=deploy" in res.output
    assert "mode=SN_SDK_CI_INSTALL type=basic" in res.output
    assert "url=https://dev.service-now.com user=admin pwd_set=yes" in res.output
    assert "s3cret" not in res.output
