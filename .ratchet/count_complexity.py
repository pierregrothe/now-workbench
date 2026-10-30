#!/usr/bin/env python3
# .ratchet/count_complexity.py
# Count functions with cyclomatic complexity > 10 (ADR-005).
# Author: Pierre Grothe
# Date: 2026-10-29
"""Count functions exceeding cyclomatic complexity threshold.

Output:
    Violations: N (or 0)
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src" / "now_workbench"
MAX_COMPLEXITY = 10


class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.complexity = 1

    def visit_If(self, node: ast.If) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.complexity += len(node.values) - 1
        self.generic_visit(node)


def check_file(path: Path) -> list[tuple[str, int, int]]:
    """Check complexity for all functions in path."""
    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(path))
    except Exception:
        return []

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor = ComplexityVisitor()
            for child in node.body:
                visitor.visit(child)
            if visitor.complexity > MAX_COMPLEXITY:
                violations.append((node.name, node.lineno, visitor.complexity))
    return violations


def main() -> int:
    if not SRC_DIR.exists():
        print("Violations: 0")
        return 0

    total_violations = 0
    for py_file in sorted(SRC_DIR.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        violations = check_file(py_file)
        for name, lineno, complexity in violations:
            print(
                f"[ERROR] {py_file.relative_to(REPO_ROOT)}:{lineno} "
                f"function '{name}' complexity {complexity} > {MAX_COMPLEXITY}",
                file=sys.stderr,
            )
            total_violations += 1

    print(f"Violations: {total_violations}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
