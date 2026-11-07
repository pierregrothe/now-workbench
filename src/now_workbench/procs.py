# src/now_workbench/procs.py
# Bounded child processes: every command gets a deadline and is fully stopped on timeout.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Process helpers (resource management).

A hung browser, SDK or npm command would otherwise run forever and hold memory, file
handles and a worker. Children start in their own process group so a timeout stops the
command and everything it started, then reaps it (no zombies).
"""

import asyncio
import contextlib
import os
import signal
from pathlib import Path
from typing import Any

__all__ = ["ProcessTimeoutError", "communicate_bounded", "spawn", "stop"]

_GRACE_S = 5.0


class ProcessTimeoutError(TimeoutError):
    """A child process did not finish before its deadline and was stopped."""


async def spawn(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    stdin: bool = False,
    merge_stderr: bool = False,
) -> asyncio.subprocess.Process:
    """Start a command in its own process group with piped output.

    Args:
        cmd: Program and arguments.
        cwd: Working directory.
        env: Full environment (inherits the parent's when None).
        stdin: Open a stdin pipe (for credentials; never pass them in arguments).
        merge_stderr: Send stderr into stdout.

    Returns:
        The running process.
    """
    kwargs: dict[str, Any] = {
        "stdout": asyncio.subprocess.PIPE,
        "stderr": asyncio.subprocess.STDOUT if merge_stderr else asyncio.subprocess.PIPE,
        "start_new_session": True,
    }
    if stdin:
        kwargs["stdin"] = asyncio.subprocess.PIPE
    if cwd is not None:
        kwargs["cwd"] = str(cwd)
    if env is not None:
        kwargs["env"] = env
    return await asyncio.create_subprocess_exec(*cmd, **kwargs)


async def stop(proc: asyncio.subprocess.Process) -> None:
    """Terminate the process group, escalate to kill after a grace period, and reap it."""
    if proc.returncode is not None:
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(proc.pid, sig)
        try:
            await asyncio.wait_for(proc.wait(), timeout=_GRACE_S)
            return
        except TimeoutError:
            continue


async def communicate_bounded(
    proc: asyncio.subprocess.Process, timeout_s: float, data: bytes | None = None
) -> tuple[bytes, bytes]:
    """Wait for a process with a deadline; stop it and raise if the deadline passes.

    Args:
        proc: A process from :func:`spawn`.
        timeout_s: Seconds to wait.
        data: Bytes for stdin.

    Returns:
        ``(stdout, stderr)``; stderr is empty when it was merged.

    Raises:
        ProcessTimeoutError: The deadline passed; the process group was stopped.
    """
    try:
        out, err = await asyncio.wait_for(proc.communicate(input=data), timeout=timeout_s)
    except TimeoutError as exc:
        await stop(proc)
        raise ProcessTimeoutError(f"stopped after {timeout_s:.0f}s without finishing") from exc
    return out or b"", err or b""
