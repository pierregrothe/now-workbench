#!/usr/bin/env python3
# .ratchet/count_no_mocks.py
# Count occurrences of mocks in tests (ADR-005 invariant: in-memory fakes only).
# Author: Pierre Grothe
# Date: 2026-10-29
"""Count mock library usages in tests.

ADR-005 strictly forbids unittest.mock, pytest_mock, MagicMock, and patch
in favor of deterministic in-memory fakes.

Output:
    Violations: N (or 0)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = REPO_ROOT / "tests"

_MOCK_PATTERNS = [
    re.compile(r"\bimport\s+mock\b"),
    re.compile(r"\bfrom\s+unittest\s+import\s+mock\b"),
    re.compile(r"\bunittest\.mock\b"),
    re.compile(r"\bpytest_mock\b"),
    re.compile(r"\bMagicMock\b"),
    re.compile(r"\bAsyncMock\b"),
    re.compile(r"\bpatch\s*\("),
    re.compile(r"@patch\b"),
]


def count_mocks() -> int:
    """Scan tests/ for mock usages and return total violation count."""
    if not TESTS_DIR.exists():
        return 0

    count = 0
    for path in sorted(TESTS_DIR.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for line_no, line in enumerate(content.splitlines(), start=1):
            for pat in _MOCK_PATTERNS:
                if pat.search(line):
                    rel_path = path.relative_to(REPO_ROOT)
                    print(
                        f"[ERROR] {rel_path}:{line_no} mock usage: {line.strip()}",
                        file=sys.stderr,
                    )
                    count += 1
                    break
    return count


def main() -> int:
    count = count_mocks()
    print(f"Violations: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
