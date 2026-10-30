#!/usr/bin/env python3
# .claude/hooks/post-edit-lint.py
# PostToolUse hook -- run ruff and mypy after editing Python files.
# Author: Pierre Grothe
# Date: 2026-10-29
"""Run ruff and mypy on modified Python files in now-workbench.

Exit codes:
  0 -- clean
  2 -- lint/type check issues found (output on stderr)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_ROOT = REPO_ROOT / "src" / "now_workbench"
TESTS_ROOT = REPO_ROOT / "tests"

_VENV_BIN_NAME = "Scripts" if sys.platform == "win32" else "bin"
_EXE_SUFFIX = ".exe" if sys.platform == "win32" else ""
VENV_BIN = REPO_ROOT / ".venv" / _VENV_BIN_NAME


def is_target(path: Path) -> bool:
    if path.suffix != ".py":
        return False
    for root in (SRC_ROOT, TESTS_ROOT):
        try:
            path.relative_to(root)
            return True
        except ValueError:
            pass
    return False


def run_tool(cmd: list[str]) -> tuple[int, str]:
    if VENV_BIN.is_dir():
        tool = VENV_BIN / f"{cmd[0]}{_EXE_SUFFIX}"
        if not tool.exists():
            return 2, f"venv tool '{cmd[0]}' not found at {tool}"
        full_cmd = [str(tool), *cmd[1:]]
    else:
        full_cmd = ["uv", "run", *cmd]
    result = subprocess.run(full_cmd, capture_output=True, text=True, cwd=REPO_ROOT, check=False)
    return result.returncode, (result.stdout + result.stderr).strip()


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError, EOFError:
        return 0

    file_path_str = data.get("tool_input", {}).get("file_path")
    if not file_path_str:
        return 0

    path = Path(file_path_str)
    if not is_target(path):
        return 0

    issues: list[str] = []

    # 1. ruff check
    ret, out = run_tool(["ruff", "check", str(path)])
    if ret != 0 and out:
        issues.append(f"ruff check:\n{out}")

    # 2. mypy (if under src/)
    try:
        path.relative_to(SRC_ROOT)
        ret, out = run_tool(["mypy", str(path)])
        if ret != 0 and out:
            issues.append(f"mypy:\n{out}")
    except ValueError:
        pass

    if issues:
        print("\n\n".join(issues), file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
