"""Tests for automated remediation engine."""

from pathlib import Path

import pytest

from now_workbench.remediation import (
    RemediationPlan,
    execute_remediation,
    inspect_remediation_needs,
    remediate_directories,
    remediate_env_file,
    remediate_sdk,
)


def test_inspect_remediation_needs() -> None:
    plan = inspect_remediation_needs()
    assert isinstance(plan, RemediationPlan)
    assert isinstance(plan.has_issues, bool)


def test_remediate_directories(tmp_path: Path) -> None:
    plan_none = RemediationPlan(
        needs_data_dir=False, needs_bundles_dir=False, needs_workspace_dir=False
    )
    actions_none = remediate_directories(plan_none)
    assert actions_none == []

    plan_all = RemediationPlan(
        needs_data_dir=True,
        needs_bundles_dir=True,
        needs_workspace_dir=True,
    )
    actions_all = remediate_directories(plan_all)
    assert len(actions_all) == 3
    assert all(a.success for a in actions_all)


def test_remediate_env_file(tmp_path: Path) -> None:
    plan_false = RemediationPlan(needs_env_file=False)
    actions_false = remediate_env_file(plan_false)
    assert actions_false == []

    # Safe test using isolated tmp_path without touching repo .env
    plan_true = RemediationPlan(needs_env_file=True)

    # 1. When .env.example does not exist in target dir
    target_env = tmp_path / ".env"
    actions_fallback = remediate_env_file(plan_true, target_dir=tmp_path)
    assert len(actions_fallback) == 1
    assert actions_fallback[0].success is True
    assert target_env.exists()
    target_env.unlink()

    # 2. When .env.example exists in target dir
    (tmp_path / ".env.example").write_text("TEST_VAR=123\n", encoding="utf-8")
    actions_copy = remediate_env_file(plan_true, target_dir=tmp_path)
    assert len(actions_copy) == 1
    assert actions_copy[0].success is True
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "TEST_VAR=123\n"


@pytest.mark.asyncio
async def test_remediate_sdk_handles_failure() -> None:
    action = await remediate_sdk(install_mode="invalid-mode", timeout_seconds=1)
    assert action.component == "ServiceNow SDK"
    assert isinstance(action.success, bool)


@pytest.mark.asyncio
async def test_remediate_sdk_npm_missing() -> None:
    action = await remediate_sdk(npm_bin="", install_mode="user")
    assert action.success is False
    assert "Node.js and npm are required" in action.details


@pytest.mark.asyncio
async def test_remediate_sdk_execution_branches() -> None:
    true_bin = "/usr/bin/true" if Path("/usr/bin/true").exists() else "/bin/true"
    act_ok = await remediate_sdk(install_mode="user", npm_bin=true_bin)
    assert act_ok.success is True
    assert "Installed @servicenow/sdk" in act_ok.details

    act_ok_global = await remediate_sdk(install_mode="global", npm_bin=true_bin)
    assert act_ok_global.success is True
    assert "globally" in act_ok_global.details

    false_bin = "/usr/bin/false" if Path("/usr/bin/false").exists() else "/bin/false"
    act_fail = await remediate_sdk(install_mode="user", npm_bin=false_bin)
    assert act_fail.success is False
    assert "failed (code 1)" in act_fail.details

    act_err = await remediate_sdk(npm_bin="/non/existent/npm/path")
    assert act_err.success is False
    assert "Installation error" in act_err.details


@pytest.mark.asyncio
async def test_execute_remediation_flags() -> None:
    actions = await execute_remediation(install_sdk_flag=False)
    assert isinstance(actions, list)

    actions_sdk = await execute_remediation(install_sdk_flag=True, timeout_seconds=1)
    assert isinstance(actions_sdk, list)
