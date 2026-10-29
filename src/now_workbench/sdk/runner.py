"""NowSdkRunner: Async orchestrator for the ServiceNow Fluent SDK (@servicenow/sdk)."""

import asyncio
import os
import shutil
from collections.abc import Awaitable, Callable
from pathlib import Path

from pydantic import BaseModel


class SdkExecutionResult(BaseModel):
    """Result of an SDK execution command."""

    command: str
    exit_code: int
    output: str
    success: bool
    duration_ms: int = 0


class NowSdkRunner:
    """Runs ServiceNow SDK operations via async subprocess with streaming logs."""

    def __init__(
        self,
        now_sdk_bin: str = "now-sdk",
        node_bin: str = "node",
        fake_mode: bool = False,
    ) -> None:
        self.now_sdk_bin = now_sdk_bin
        self.node_bin = node_bin
        self.fake_mode = fake_mode

    def probe_environment(self) -> dict[str, str | bool]:
        """Check availability of Node.js and now-sdk."""
        node_path = shutil.which(self.node_bin)
        sdk_path = shutil.which(self.now_sdk_bin)
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
    ) -> SdkExecutionResult:
        """Execute a now-sdk subcommand and stream stdout/stderr lines."""
        cmd_str = " ".join([self.now_sdk_bin] + args)

        if self.fake_mode:
            fake_log = f"[fake-sdk] Executed: {cmd_str} in {cwd}\n"
            if stream_callback:
                await stream_callback(fake_log)
            return SdkExecutionResult(
                command=cmd_str,
                exit_code=0,
                output=fake_log,
                success=True,
            )

        # Check binary existence
        if not shutil.which(self.now_sdk_bin):
            err_msg = (
                f"Error: '{self.now_sdk_bin}' not found in PATH. "
                "Ensure @servicenow/sdk is installed via npm."
            )
            if stream_callback:
                await stream_callback(f"[error] {err_msg}\n")
            return SdkExecutionResult(
                command=cmd_str,
                exit_code=127,
                output=err_msg,
                success=False,
            )

        proc = await asyncio.create_subprocess_exec(
            self.now_sdk_bin,
            *args,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "CI": "1"},
        )

        output_lines: list[str] = []
        if proc.stdout:
            while True:
                line_bytes = await proc.stdout.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace")
                output_lines.append(line)
                if stream_callback:
                    await stream_callback(line)

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
    ) -> SdkExecutionResult:
        """Deploy compiled application metadata to the target ServiceNow instance."""
        return await self.run_command(["deploy"], cwd=project_dir, stream_callback=stream_callback)
