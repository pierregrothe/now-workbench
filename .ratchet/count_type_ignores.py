#!/usr/bin/env python3
# .ratchet/count_type_ignores.py
# Count occurrences of type: ignore in src/ (ADR-005 burndown ratchet).
# Author: Pierre Grothe
# Date: 2026-10-29
"""Count `# type: ignore` annotations in src/.

Output:
    Violations: N (or 0)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src" / "now_workbench"

_TYPE_IGNORE_RE = re.compile(r"#\s*type:\s*ignore\b")


def main() -> int:
    if not SRC_DIR.exists():
        print("Violations: 0")
        return 0

    count = 0
    for path in sorted(SRC_DIR.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for line_no, line in enumerate(content.splitlines(), start=1):
            if _TYPE_IGNORE_RE.search(line):
                rel_path = path.relative_to(REPO_ROOT)
                print(
                    f"[ERROR] {rel_path}:{line_no} type ignore: {line.strip()}",
                    file=sys.stderr,
                )
                count += 1

    print(f"Violations: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
