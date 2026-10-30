#!/usr/bin/env python3
# .claude/hooks/pre-edit-validate.py
# PreToolUse hook -- block prohibited patterns before writing to disk.
# Author: Pierre Grothe
# Date: 2026-10-29
"""Block prohibited patterns before any Python file is written in now-workbench.

Constitutional invariants enforced (ADR-005):
  1. ASCII-only source code (no emoji or decorative symbols).
  2. No sys.argv indexing (use Typer CLI parameters).
  3. No bare Any in signatures.
  4. In-memory fakes only (bans mock, MagicMock, patch in tests).
  5. Subprocess & async stream safety (bans blocking subprocess.run in async def).
  6. Absolute imports only (bans relative imports in src/).

Exit codes:
  0 -- clean
  2 -- prohibited pattern detected (blocks the write)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_ROOT = REPO_ROOT / "src" / "now_workbench"
TESTS_ROOT = REPO_ROOT / "tests"

_EMOJI_RE = re.compile("[\U0001f000-\U0001ffff\U00002600-\U000026ff\U00002700-\U000027bf]")
_SYS_ARGV_RE = re.compile(r"sys\.argv\[")
_MOCK_RE = re.compile(r"\b(unittest\.mock|pytest_mock|MagicMock|AsyncMock|patch\s*\(|@patch\b)")
_RELATIVE_IMPORT_RE = re.compile(r"^\s*from\s+\.\.?\w*\s+import\b", re.MULTILINE)
_BLOCKING_SUBPROCESS_RE = re.compile(r"subprocess\.(run|call|check_output|check_call)\(")


def is_project_python(path: Path) -> bool:
    """Return True if path is a tracked Python file."""
    if path.suffix != ".py":
        return False
    for root in (SRC_ROOT, TESTS_ROOT):
        try:
            path.relative_to(root)
            return True
        except ValueError:
            pass
    return False


def is_test_file(path: Path) -> bool:
    try:
        path.relative_to(TESTS_ROOT)
        return True
    except ValueError:
        return False


def is_src_file(path: Path) -> bool:
    try:
        path.relative_to(SRC_ROOT)
        return True
    except ValueError:
        return False


def check_emoji(content: str, path: Path) -> str | None:
    match = _EMOJI_RE.search(content)
    if match:
        char = match.group()
        return (
            f"BLOCKED: emoji character U+{ord(char):04X} in {path.name}. "
            "now-workbench enforces ASCII-only codebase (ADR-005)."
        )
    return None


def check_sys_argv(content: str, path: Path) -> str | None:
    if is_test_file(path):
        return None
    if _SYS_ARGV_RE.search(content):
        return f"BLOCKED: sys.argv indexing in {path.name}. Use Typer parameters (ADR-005)."
    return None


def check_mocks(content: str, path: Path) -> str | None:
    if not is_test_file(path):
        return None
    match = _MOCK_RE.search(content)
    if match:
        return (
            f"BLOCKED: Mock usage '{match.group(1)}' in {path.name}. "
            "now-workbench requires deterministic in-memory fakes (ADR-005)."
        )
    return None


def check_relative_imports(content: str, path: Path) -> str | None:
    if not is_src_file(path):
        return None
    if _RELATIVE_IMPORT_RE.search(content):
        return (
            f"BLOCKED: Relative import in {path.name}. "
            "Use absolute imports 'from now_workbench.<module>' (ADR-005)."
        )
    return None


def check_blocking_subprocess(content: str, path: Path) -> str | None:
    if not is_src_file(path):
        return None
    # Check if blocking subprocess appears inside async def
    if "async def " in content and _BLOCKING_SUBPROCESS_RE.search(content):
        return (
            f"BLOCKED: Blocking subprocess invocation in async module {path.name}. "
            "Use asyncio.create_subprocess_exec with log streaming (ADR-005)."
        )
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError, EOFError:
        return 0

    file_path_str = data.get("tool_input", {}).get("file_path")
    if not file_path_str:
        return 0

    path = Path(file_path_str)
    if not is_project_python(path):
        return 0

    content = (
        data.get("tool_input", {}).get("new_string")
        or data.get("tool_input", {}).get("content")
        or ""
    )
    if not content:
        return 0

    checks = [
        check_emoji,
        check_sys_argv,
        check_mocks,
        check_relative_imports,
        check_blocking_subprocess,
    ]

    for check in checks:
        if violation := check(content, path):
            print(violation, file=sys.stderr)
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
