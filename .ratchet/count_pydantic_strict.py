#!/usr/bin/env python3
"""Count Pydantic BaseModel subclasses in src/ missing extra='forbid' or frozen=True."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src" / "now_workbench"


def main() -> int:
    violations = 0
    for path in sorted(SRC_DIR.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = [ast.unparse(b) for b in node.bases]
            if "BaseModel" not in bases:
                continue
            class_src = ast.unparse(node)
            has_extra = 'extra="forbid"' in class_src or "extra='forbid'" in class_src
            has_frozen = "frozen=True" in class_src
            if not (has_extra and has_frozen):
                rel = path.relative_to(REPO_ROOT)
                print(
                    f"[ERROR] {rel}:{node.lineno} {node.name} missing "
                    "ConfigDict(extra='forbid', frozen=True) (ADR-005)"
                )
                violations += 1

    print(f"Violations: {violations}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
