#!/usr/bin/env python3
# .agents/scripts/pre_tool_guard.py
# Antigravity PreToolUse hook for now-workbench.
# Author: Pierre Grothe
# Date: 2026-10-29
"""PreToolUse guard validating content before write_file or edit_file executes.

Enforces ADR-005 invariants:
  - ASCII-only content (no emoji).
  - In-memory fakes only (bans mock, MagicMock, patch in tests/).
  - Absolute imports in src/ (no relative imports).
  - Subprocess safety in async def.
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
_MOCK_RE = re.compile(r"\b(unittest\.mock|pytest_mock|MagicMock|AsyncMock|patch\s*\(|@patch\b)")
_RELATIVE_IMPORT_RE = re.compile(r"^\s*from\s+\.\.?\w*\s+import\b", re.MULTILINE)
_BLOCKING_SUBPROCESS_RE = re.compile(r"subprocess\.(run|call|check_output|check_call)\(")


def validate(path_str: str, content: str) -> str | None:
    if not path_str.endswith(".py"):
        return None

    raw = Path(path_str)
    path = raw.resolve() if raw.is_absolute() else (REPO_ROOT / raw).resolve()

    # 1. ASCII-only
    if _EMOJI_RE.search(content):
        msg = f"Emoji character detected in {path.name}."
        return f"{msg} now-workbench requires ASCII-only (ADR-005)."

    # 2. Test file checks
    try:
        path.relative_to(TESTS_ROOT)
        match = _MOCK_RE.search(content)
        if match:
            return (
                f"Mock usage '{match.group(1)}' detected in {path.name}. "
                "now-workbench requires in-memory fakes (ADR-005)."
            )
    except ValueError:
        pass

    # 3. Source file checks
    try:
        path.relative_to(SRC_ROOT)
        if _RELATIVE_IMPORT_RE.search(content):
            return (
                f"Relative import detected in {path.name}. "
                "Use absolute imports 'from now_workbench.<pkg>' (ADR-005)."
            )
        if "async def " in content and _BLOCKING_SUBPROCESS_RE.search(content):
            return (
                f"Blocking subprocess call inside async def in {path.name}. "
                "Use asyncio.create_subprocess_exec (ADR-005)."
            )
    except ValueError:
        pass

    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.stdout.write(json.dumps({"decision": "allow"}))
        return 0

    tool_call = data.get("toolCall", {})
    name = tool_call.get("name", "")
    args = tool_call.get("args", {})

    path_str = args.get("Path", "")
    content = args.get("Content") or args.get("Replacement") or ""

    if name in ("write_file", "edit_file") and path_str and content:
        err = validate(path_str, content)
        if err:
            out = {
                "decision": "deny",
                "reason": f"BLOCKED by Antigravity PreTool Guard (ADR-005): {err}",
            }
            sys.stdout.write(json.dumps(out))
            return 0

    sys.stdout.write(json.dumps({"decision": "allow"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
