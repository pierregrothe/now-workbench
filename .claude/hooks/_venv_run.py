#!/usr/bin/env python3
# .claude/hooks/_venv_run.py
# Cross-platform venv-tool launcher used by .pre-commit-config.yaml.
# Author: Pierre Grothe
# Date: 2026-10-29
"""Invoke a tool installed in the project venv with forwarded args.

Pre-commit's ``language: system`` requires the ``entry:`` line to be a literal
command. A literal ``.venv/bin/ruff`` only works on POSIX; ``.venv/Scripts/
ruff.exe`` only on Windows. This launcher abstracts the difference so a
single entry line works across operating systems:

    entry: python .claude/hooks/_venv_run.py ruff check src/ tests/

The launcher resolves ``<tool>`` against ``.venv/Scripts/`` on Windows or
``.venv/bin/`` on macOS / Linux, then exec's it with the forwarded args.

Exit codes:
    1 -- venv missing or tool not present (run ``uv sync`` first)
    Whatever the tool itself returns
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

if sys.platform == "win32":
    _VENV_BIN = REPO_ROOT / ".venv" / "Scripts"
    _EXE_SUFFIX = ".exe"
else:
    _VENV_BIN = REPO_ROOT / ".venv" / "bin"
    _EXE_SUFFIX = ""


def main() -> int:
    """Run ``argv[1]`` from the project venv with ``argv[2:]`` as its args."""
    if len(sys.argv) < 2:
        print("usage: _venv_run.py <tool> [args...]", file=sys.stderr)
        return 1

    tool_name = sys.argv[1]
    tool_args = sys.argv[2:]
    tool_path = _VENV_BIN / f"{tool_name}{_EXE_SUFFIX}"
    if not tool_path.exists():
        # Fallback to uv run if binary not directly found
        res = subprocess.run(["uv", "run", tool_name, *tool_args], check=False)
        return res.returncode

    return subprocess.run([str(tool_path), *tool_args], check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
