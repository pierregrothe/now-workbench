"""Automated environment and toolchain remediation for now-workbench."""

import os
import shutil
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from now_workbench.config.settings import settings
from now_workbench.procs import communicate_bounded, spawn
from now_workbench.sdk.runner import NowSdkRunner


class RemediationAction(BaseModel):
    """Result of an individual remediation step."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    component: str
    action: str
    success: bool
    details: str


class RemediationPlan(BaseModel):
    """Diagnosed issues and remediation tasks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    needs_sdk_install: bool = False
    needs_data_dir: bool = False
    needs_bundles_dir: bool = False
    needs_workspace_dir: bool = False
    needs_env_file: bool = False

    @property
    def has_issues(self) -> bool:
        """Return True if any remediation task is pending."""
        return any(
            [
                self.needs_sdk_install,
                self.needs_data_dir,
                self.needs_bundles_dir,
                self.needs_workspace_dir,
                self.needs_env_file,
            ]
        )


def inspect_remediation_needs() -> RemediationPlan:
    """Analyze current environment and identify remediable issues."""
    runner = NowSdkRunner(now_sdk_bin=settings.now_sdk_bin, node_bin=settings.node_bin)
    probe = runner.probe_environment()

    root_dir = Path.cwd()
    data_dir = settings.get_data_dir()
    bundles_dir = Path(os.environ.get("WORKBENCH_BUNDLES_DIR", settings.bundles_dir))
    workspace_dir = Path(os.environ.get("WORKBENCH_WORKSPACE_DIR", settings.workspace_dir))
    env_file = root_dir / ".env"
    env_example = root_dir / ".env.example"

    return RemediationPlan(
        needs_sdk_install=not bool(probe["now_sdk_available"]),
        needs_data_dir=not data_dir.exists(),
        needs_bundles_dir=not bundles_dir.exists(),
        needs_workspace_dir=not workspace_dir.exists(),
        needs_env_file=(not env_file.exists()) and env_example.exists(),
    )


def remediate_directories(plan: RemediationPlan) -> list[RemediationAction]:
    """Create missing runtime storage directories."""
    actions: list[RemediationAction] = []
    data_dir = settings.get_data_dir()
    bundles_dir = Path(os.environ.get("WORKBENCH_BUNDLES_DIR", settings.bundles_dir))
    workspace_dir = Path(os.environ.get("WORKBENCH_WORKSPACE_DIR", settings.workspace_dir))
    targets = [
        ("Data Directory", data_dir, plan.needs_data_dir),
        ("Bundles Directory", bundles_dir, plan.needs_bundles_dir),
        ("Workspaces Directory", workspace_dir, plan.needs_workspace_dir),
    ]
    for name, path, needed in targets:
        if needed:
            path.mkdir(parents=True, exist_ok=True)
            actions.append(
                RemediationAction(
                    component=name,
                    action="create_directory",
                    success=True,
                    details=f"Created directory at {path}",
                )
            )
    return actions


def remediate_env_file(
    plan: RemediationPlan, target_dir: Path | None = None
) -> list[RemediationAction]:
    """Copy .env.example to .env if missing, or create starter .env."""
    if not plan.needs_env_file:
        return []
    base = target_dir or Path.cwd()
    example = base / ".env.example"
    target_env = base / ".env"
    if example.exists():
        shutil.copy(example, target_env)
    else:
        target_env.write_text("# now-workbench environment\n", encoding="utf-8")
    return [
        RemediationAction(
            component="Environment Configuration",
            action="copy_env_example",
            success=True,
            details="Created .env configuration file",
        )
    ]


async def remediate_sdk(
    install_mode: str = "user",
    timeout_seconds: int = 120,
    npm_bin: str | None = None,
) -> RemediationAction:
    """Install @servicenow/sdk asynchronously via npm."""
    resolved_npm = npm_bin if npm_bin is not None else shutil.which("npm")
    if not resolved_npm:
        return RemediationAction(
            component="ServiceNow SDK",
            action="install_sdk",
            success=False,
            details="Node.js and npm are required. Please install Node.js 20+ first.",
        )

    if install_mode == "user":
        user_dir = Path.home() / ".now-workbench" / "sdk"
        user_dir.mkdir(parents=True, exist_ok=True)
        cmd = [resolved_npm, "install", "--prefix", str(user_dir), "@servicenow/sdk"]
        desc = f"Installed @servicenow/sdk locally into {user_dir}"
    else:
        cmd = [resolved_npm, "install", "-g", "@servicenow/sdk"]
        desc = "Installed @servicenow/sdk globally"

    try:
        proc = await spawn(cmd, env=os.environ.copy())
        stdout, stderr = await communicate_bounded(proc, float(timeout_seconds))
        if proc.returncode == 0:
            return RemediationAction(
                component="ServiceNow SDK",
                action="install_sdk",
                success=True,
                details=desc,
            )
        err_msg = stderr.decode("utf-8", errors="replace").strip()
        out_msg = stdout.decode("utf-8", errors="replace").strip()
        return RemediationAction(
            component="ServiceNow SDK",
            action="install_sdk",
            success=False,
            details=f"npm install failed (code {proc.returncode}): {err_msg or out_msg}",
        )
    except TimeoutError:
        return RemediationAction(
            component="ServiceNow SDK",
            action="install_sdk",
            success=False,
            details=f"Installation timed out after {timeout_seconds}s.",
        )
    except Exception as exc:
        return RemediationAction(
            component="ServiceNow SDK",
            action="install_sdk",
            success=False,
            details=f"Installation error: {exc}",
        )


async def execute_remediation(
    install_mode: str = "user",
    install_sdk_flag: bool = True,
    timeout_seconds: int | None = None,
) -> list[RemediationAction]:
    """Execute complete remediation plan for detected issues."""
    timeout = (
        timeout_seconds
        if timeout_seconds is not None
        else int(os.environ.get("REMEDIATION_TIMEOUT", "120"))
    )
    plan = inspect_remediation_needs()
    results: list[RemediationAction] = []

    results.extend(remediate_directories(plan))
    results.extend(remediate_env_file(plan))

    if plan.needs_sdk_install and install_sdk_flag:
        sdk_action = await remediate_sdk(install_mode=install_mode, timeout_seconds=timeout)
        results.append(sdk_action)

    return results
