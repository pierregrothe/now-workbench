#!/usr/bin/env python3
# .ratchet/count_absolute_imports.py
# Count occurrences of relative imports in src/ (ADR-005 absolute imports invariant).
# Author: Pierre Grothe
# Date: 2026-10-29
"""Count relative imports in src/.

ADR-005 strictly mandates absolute imports (from now_workbench.<pkg> import ...)
over relative imports.

Output:
    Violations: N (or 0)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src" / "now_workbench"

_RELATIVE_IMPORT_RE = re.compile(r"^\s*from\s+\.\.?\w*\s+import\b")


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
            if _RELATIVE_IMPORT_RE.search(line):
                rel_path = path.relative_to(REPO_ROOT)
                print(
                    f"[ERROR] {rel_path}:{line_no} relative import: {line.strip()}",
                    file=sys.stderr,
                )
                count += 1

    print(f"Violations: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
