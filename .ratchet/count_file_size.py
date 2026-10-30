#!/usr/bin/env python3
# .ratchet/count_file_size.py
# Ratchet wrapper for scripts/check_file_sizes.py.
# Author: Pierre Grothe
# Date: 2026-10-29
"""Count file size violations exceeding limits.

Output:
    Violations: N (or 0)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_file_sizes.py"


def main() -> int:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=False,
    )
    violations = 0
    for line in result.stderr.splitlines():
        if "lines exceeds limit" in line or "must not grow" in line:
            violations += 1
            print(f"[ERROR] {line}", file=sys.stderr)

    print(f"Violations: {violations}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
