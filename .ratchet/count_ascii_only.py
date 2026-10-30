#!/usr/bin/env python3
"""Count files containing non-ASCII characters across src/, tests/, web/src/, and .primer/."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_DIRS = ["src", "tests", "web/src", ".primer"]
ALLOWED_SUFFIXES = {".py", ".ts", ".css", ".md", ".yaml", ".json"}


def main() -> int:
    violations = 0
    for folder in TARGET_DIRS:
        root = REPO_ROOT / folder
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in ALLOWED_SUFFIXES:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                print(f"[ERROR] {path.relative_to(REPO_ROOT)}: non-UTF-8 encoding")
                violations += 1
                continue
            for line_no, line in enumerate(content.splitlines(), start=1):
                if any(ord(ch) > 127 for ch in line):
                    rel = path.relative_to(REPO_ROOT)
                    print(f"[ERROR] {rel}:{line_no} non-ASCII character detected (ADR-005)")
                    violations += 1
                    break

    print(f"Violations: {violations}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
