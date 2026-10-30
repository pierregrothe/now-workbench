#!/usr/bin/env python3
# .claude/hooks/_run.py
# Cross-platform launcher: find the project venv Python and run a hook.
# Author: Pierre Grothe
# Date: 2026-10-29
"""Launcher for Claude Code hooks.

Bootstrap Python (from settings.json) re-execs into the project venv Python
when one exists, so hook scripts always see the same interpreter and tooling
that the project uses for pytest/ruff/mypy. If no venv exists yet, falls
back to ``sys.executable``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _venv_python() -> Path:
    """Return the project venv Python path for the current OS."""
    if sys.platform == "win32":
        return REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    return REPO_ROOT / ".venv" / "bin" / "python"


def main() -> int:
    """Resolve the target hook and re-exec it under the venv Python."""
    if len(sys.argv) < 2:
        return 0

    hook_name = sys.argv[1]
    hook_path = REPO_ROOT / ".claude" / "hooks" / f"{hook_name}.py"
    if not hook_path.exists():
        return 0

    venv = _venv_python()
    python_exe = str(venv) if venv.exists() else sys.executable

    result = subprocess.run([python_exe, str(hook_path)], stdin=sys.stdin, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
