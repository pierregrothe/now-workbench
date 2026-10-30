#!/usr/bin/env python3
"""Count blocking subprocess calls inside async def functions in src/."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src" / "now_workbench"
BLOCKING_CALLS = {
    "subprocess.run",
    "subprocess.call",
    "subprocess.check_output",
    "subprocess.check_call",
}


def main() -> int:
    violations = 0
    for path in sorted(SRC_DIR.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    func_name = ast.unparse(child.func)
                    if func_name in BLOCKING_CALLS:
                        rel = path.relative_to(REPO_ROOT)
                        print(
                            f"[ERROR] {rel}:{child.lineno} blocking '{func_name}' inside "
                            f"async function '{node.name}' (ADR-005)"
                        )
                        violations += 1

    print(f"Violations: {violations}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
