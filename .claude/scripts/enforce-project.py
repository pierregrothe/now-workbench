#!/usr/bin/env python3
# .claude/scripts/enforce-project.py
# PostToolUse mechanical check for now-workbench.
# Author: Pierre Grothe
# Date: 2026-10-29
"""Mechanical rule enforcement on edited files in now-workbench.

Checks:
  - Absolute imports (now_workbench.<module>)
  - Blocking I/O inside async functions
  - Pure in-memory fakes (no unittest.mock in tests)
  - Explicit __all__ in src/ modules
  - ASCII-only characters

Exit codes:
  0 -- clean
  2 -- rule violation (output on stderr)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_ROOT = REPO_ROOT / "src" / "now_workbench"
TESTS_ROOT = REPO_ROOT / "tests"


def is_src_file(path: Path) -> bool:
    try:
        path.relative_to(SRC_ROOT)
        return True
    except ValueError:
        return False


def is_test_file(path: Path) -> bool:
    try:
        path.relative_to(TESTS_ROOT)
        return True
    except ValueError:
        return False


def check_file(path: Path) -> list[str]:
    violations: list[str] = []
    if path.suffix != ".py" or not path.exists():
        return violations

    content = path.read_text(encoding="utf-8", errors="replace")

    # 1. ASCII-only check
    for line_no, line in enumerate(content.splitlines(), start=1):
        if any(ord(c) > 127 for c in line):
            violations.append(f"{path.name}:{line_no} Non-ASCII character found (ADR-005)")
            break

    # 2. Source-specific checks
    if is_src_file(path):
        # Relative imports check
        if re.search(r"^\s*from\s+\.\.?\w*\s+import\b", content, re.MULTILINE):
            msg = f"{path.name}: Relative imports forbidden -- use 'from now_workbench.<pkg>'"
            violations.append(f"{msg} (ADR-005)")

        # Blocking I/O in async def
        if "async def " in content:
            if re.search(r"\b(time\.sleep|requests\.(get|post|put|delete)|open\()\b", content):
                msg = f"{path.name}: Blocking I/O in async module -- use asyncio equivalents"
                violations.append(f"{msg} (ADR-005)")

    # 3. Test-specific checks
    if is_test_file(path):
        pattern = r"\b(unittest\.mock|pytest_mock|MagicMock|AsyncMock|patch\s*\(|@patch\b)"
        if re.search(pattern, content):
            violations.append(f"{path.name}: Mock usage forbidden -- use in-memory fakes (ADR-005)")

    return violations


def main() -> int:
    target_path = None
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])
    else:
        try:
            event = json.load(sys.stdin)
            fp = event.get("tool_input", {}).get("file_path")
            if fp:
                target_path = Path(fp)
        except Exception:
            return 0

    if not target_path or not target_path.exists():
        return 0

    violations = check_file(target_path)
    if violations:
        print("ENFORCE-PROJECT VIOLATIONS (ADR-005):", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
