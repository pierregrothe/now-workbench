"""NowSdkRunner: Async orchestrator for the ServiceNow Fluent SDK (@servicenow/sdk)."""

import asyncio
import os
import shutil
from collections.abc import Awaitable, Callable
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class SdkExecutionResult(BaseModel):
    """Result of an SDK execution command."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    command: str
    exit_code: int
    output: str
    success: bool
    duration_ms: int = 0


async def _stream_lines(
    stream: asyncio.StreamReader,
    callback: Callable[[str], Awaitable[None]] | None,
) -> list[str]:
    """Read lines from async stream and invoke callback."""
    lines: list[str] = []
    while True:
        line_bytes = await stream.readline()
        if not line_bytes:
            break
        line = line_bytes.decode("utf-8", errors="replace")
        lines.append(line)
        if callback:
            await callback(line)
    return lines


class NowSdkRunner:
    """Runs ServiceNow SDK operations via async subprocess with streaming logs."""

    def __init__(
        self,
        now_sdk_bin: str = "now-sdk",
        node_bin: str = "node",
        fake_mode: bool = False,
        sdk_candidates: tuple[str, ...] = ("snc", "now-sdk"),
        user_local_dir: Path | None = None,
    ) -> None:
        self.now_sdk_bin = now_sdk_bin
        self.node_bin = node_bin
        self.fake_mode = fake_mode
        self.sdk_candidates = sdk_candidates
        self.user_local_dir = (
            user_local_dir
            if user_local_dir is not None
            else (Path.home() / ".now-workbench" / "sdk" / "node_modules" / ".bin")
        )

    def resolve_sdk_bin(self) -> str | None:
        """Resolve executable path for now-sdk."""
        if shutil.which(self.now_sdk_bin):
            return shutil.which(self.now_sdk_bin)
        user_local = self.user_local_dir / self.now_sdk_bin
        if user_local.is_file() and os.access(user_local, os.X_OK):
            return str(user_local)
        for candidate in self.sdk_candidates:
            found = shutil.which(candidate)
            if found:
                return found
        return None

    def probe_environment(self) -> dict[str, str | bool]:
        """Check availability of Node.js and now-sdk."""
        node_path = shutil.which(self.node_bin)
        sdk_path = self.resolve_sdk_bin()
        return {
            "node_available": node_path is not None or self.fake_mode,
            "node_path": node_path or ("fake_node" if self.fake_mode else ""),
            "now_sdk_available": sdk_path is not None or self.fake_mode,
            "now_sdk_path": sdk_path or ("fake_now_sdk" if self.fake_mode else ""),
        }

    async def run_command(
        self,
        args: list[str],
        cwd: Path,
        stream_callback: Callable[[str], Awaitable[None]] | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> SdkExecutionResult:
        """Execute a now-sdk subcommand and stream stdout/stderr lines."""
        resolved_bin = self.resolve_sdk_bin() or self.now_sdk_bin
        cmd_str = " ".join([resolved_bin] + args)

        if self.fake_mode:
            target_info = (
                f" (target: {extra_env.get('SN_SDK_INSTANCE_URL')})"
                if extra_env and "SN_SDK_INSTANCE_URL" in extra_env
                else ""
            )
            fake_log = f"[fake-sdk] Executed: {cmd_str} in {cwd}{target_info}\n"
            if stream_callback:
                await stream_callback(fake_log)
            return SdkExecutionResult(
                command=cmd_str,
                exit_code=0,
                output=fake_log,
                success=True,
            )

        # Check binary existence
        if not self.resolve_sdk_bin():
            err_msg = (
                f"Error: '{self.now_sdk_bin}' not found in PATH or ~/.now-workbench/sdk. "
                "Run 'workbench doctor --fix' or 'npm install -g @servicenow/sdk'."
            )
            if stream_callback:
                await stream_callback(f"[error] {err_msg}\n")
            return SdkExecutionResult(
                command=cmd_str,
                exit_code=127,
                output=err_msg,
                success=False,
            )

        proc_env = {**os.environ, "CI": "1", **(extra_env or {})}
        proc = await asyncio.create_subprocess_exec(
            resolved_bin,
            *args,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=proc_env,
        )

        output_lines: list[str] = []
        if proc.stdout:
            output_lines = await _stream_lines(proc.stdout, stream_callback)

        await proc.wait()
        exit_code = proc.returncode or 0
        full_output = "".join(output_lines)

        return SdkExecutionResult(
            command=cmd_str,
            exit_code=exit_code,
            output=full_output,
            success=exit_code == 0,
        )

    async def build(
        self,
        project_dir: Path,
        stream_callback: Callable[[str], Awaitable[None]] | None = None,
    ) -> SdkExecutionResult:
        """Compile ServiceNow Fluent TypeScript files."""
        return await self.run_command(["build"], cwd=project_dir, stream_callback=stream_callback)

    async def deploy(
        self,
        project_dir: Path,
        stream_callback: Callable[[str], Awaitable[None]] | None = None,
        instance_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> SdkExecutionResult:
        """Deploy compiled application metadata to the target ServiceNow instance.

        Credentials use the SDK's non-interactive CI mode (``SN_SDK_NODE_ENV=SN_SDK_CI_INSTALL``
        with ``SN_SDK_INSTANCE_URL``/``SN_SDK_USER``/``SN_SDK_USER_PWD``, read from the
        @servicenow/sdk 4.14 sources), so no ``now-sdk auth`` alias has to exist on the host.
        They travel in the child's environment only, never in its arguments.
        """
        extra_env: dict[str, str] = {}
        if instance_url and username and password:
            extra_env = {
                "SN_SDK_NODE_ENV": "SN_SDK_CI_INSTALL",
                "SN_SDK_AUTH_TYPE": "basic",
                "SN_SDK_INSTANCE_URL": instance_url,
                "SN_SDK_USER": username,
                "SN_SDK_USER_PWD": password,
            }

        return await self.run_command(
            ["deploy"],
            cwd=project_dir,
            stream_callback=stream_callback,
            extra_env=extra_env,
        )
