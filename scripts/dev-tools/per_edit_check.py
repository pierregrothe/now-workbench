#!/usr/bin/env python3
# scripts/dev-tools/per_edit_check.py
# Per-edit project-rule check for Claude Code and Antigravity.
# Author: Pierre Grothe
# Date: 2026-10-29
"""Per-edit project rule check for now-workbench.

Runs fast syntactic and AST checks on a single modified Python file.
Designed for Claude Code PostToolUse and Antigravity lifecycle hooks.

Checks (ADR-005):
  - ASCII-only characters (no emoji or non-ASCII characters).
  - Absolute imports in src/ (no relative imports).
  - In-memory fakes only (no unittest.mock/pytest_mock/patch in tests/).
  - Subprocess safety in async functions (no blocking subprocess.run in async def).
  - Function cyclomatic complexity <= 10.
  - File size limits (src <= 800, tests <= 1000 lines).

Usage:
    python scripts/dev-tools/per_edit_check.py <file_path> [--format claude|text]

Output:
  - claude: JSON with hookSpecificOutput.additionalContext.
  - text: plain text to stdout.
"""

from __future__ import annotations

import argparse
import ast
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

MAX_COMPLEXITY = 10
SRC_LIMIT = 800
TEST_LIMIT = 1000


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

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.complexity += len(node.values) - 1
        self.generic_visit(node)


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

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [f"{path.name}: Non-UTF-8 / binary content detected"]

    # 1. ASCII-only check
    for line_no, line in enumerate(content.splitlines(), start=1):
        if any(ord(c) > 127 for c in line):
            violations.append(f"{path.name}:{line_no} Non-ASCII character found (ADR-005)")
            break

    # 2. File size limit
    line_count = len(content.splitlines())
    if is_src_file(path) and line_count > SRC_LIMIT:
        msg = f"{path.name}: {line_count} lines exceeds limit of {SRC_LIMIT}"
        violations.append(f"{msg} (ADR-005)")
    elif is_test_file(path) and line_count > TEST_LIMIT:
        msg = f"{path.name}: {line_count} lines exceeds limit of {TEST_LIMIT}"
        violations.append(f"{msg} (ADR-005)")

    # 3. Source-specific checks
    if is_src_file(path):
        if _RELATIVE_IMPORT_RE.search(content):
            msg = f"{path.name}: Relative import forbidden -- use 'from now_workbench.<pkg>'"
            violations.append(f"{msg} (ADR-005)")
        if "async def " in content and _BLOCKING_SUBPROCESS_RE.search(content):
            msg = f"{path.name}: Blocking subprocess in async function"
            violations.append(f"{msg} -- use asyncio.create_subprocess_exec (ADR-005)")

    # 4. Test-specific checks
    if is_test_file(path):
        match = _MOCK_RE.search(content)
        if match:
            msg = f"{path.name}: Mock usage '{match.group(1)}' forbidden"
            violations.append(f"{msg} -- use in-memory fakes (ADR-005)")

    # 5. Complexity & Pydantic strictness AST check
    try:
        tree = ast.parse(content, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visitor = ComplexityVisitor()
                for child in node.body:
                    visitor.visit(child)
                if visitor.complexity > MAX_COMPLEXITY:
                    violations.append(
                        f"{path.name}:{node.lineno} function '{node.name}' "
                        f"complexity {visitor.complexity} > {MAX_COMPLEXITY} (ADR-005)"
                    )
            elif is_src_file(path) and isinstance(node, ast.ClassDef):
                bases = [ast.unparse(b) for b in node.bases]
                if "BaseModel" in bases:
                    src_seg = ast.unparse(node)
                    has_extra = 'extra="forbid"' in src_seg or "extra='forbid'" in src_seg
                    has_frozen = "frozen=True" in src_seg
                    if not (has_extra and has_frozen):
                        violations.append(
                            f"{path.name}:{node.lineno} class '{node.name}' missing "
                            "ConfigDict(extra='forbid', frozen=True) (ADR-005)"
                        )
    except SyntaxError as e:
        violations.append(f"{path.name}:{e.lineno} SyntaxError: {e.msg}")

    return violations


def _emit_claude(violations: list[str]) -> None:
    if not violations:
        return
    msg = "Project rule violations (ADR-005):\n" + "\n".join(f"  - {v}" for v in violations)
    payload = {
        "suppressOutput": True,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        },
    }
    print(json.dumps(payload))


def _emit_text(violations: list[str]) -> None:
    if not violations:
        return
    print("Project rule violations (ADR-005):")
    for v in violations:
        print(f"  - {v}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Per-edit project rule check.")
    parser.add_argument("file", nargs="?", default=None, help="Path to .py file")
    parser.add_argument("--format", choices=["claude", "text"], default="claude")
    args = parser.parse_args()

    file_arg = args.file
    if (not file_arg or file_arg.startswith("$")) and not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                data = json.loads(stdin_data)
                tool_input = data.get("tool_input", {})
                args_dict = data.get("toolCall", {}).get("args", {}) or data.get("args", {})
                combined = {**tool_input, **args_dict}
                for key in ["TargetFile", "file_path", "path", "file", "Path"]:
                    if key in combined:
                        file_arg = combined[key]
                        break
        except Exception:
            pass

    if not file_arg:
        sys.exit(0)

    target_path = Path(file_arg)
    if target_path.suffix != ".py" or not target_path.exists():
        sys.exit(0)

    violations = check_file(target_path)
    if args.format == "claude":
        _emit_claude(violations)
    else:
        _emit_text(violations)

    sys.exit(0)


if __name__ == "__main__":
    main()
