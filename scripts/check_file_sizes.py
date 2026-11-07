#!/usr/bin/env python3
# scripts/check_file_sizes.py
# Enforce ADR-005 file-size limits with a ratchet for grandfathered files.
# Author: Pierre Grothe
# Date: 2026-10-29
"""Check that source files stay within the size limits of ADR-005 as amended by ADR-015.

Limits:
    src/now_workbench/                          -- 500 lines
    src/now_workbench/**/_internal/             -- 800 lines
    models / config / enums / protocols / constants modules -- 1000 lines
    tests/                                      -- 1000 lines
    web/src/**/*.ts                             -- 500 lines

Files already over the limit when this script was first introduced are
listed in ``.file-size-baseline.json`` at their current size. The ratchet
allows those files to shrink (or stay equal) but never to grow.

Exit codes:
    0 -- all checks pass
    1 -- one or more violations
    2 -- baseline file is malformed
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

__all__ = ["main", "src_limit"]

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src" / "now_workbench"
TESTS_ROOT = REPO_ROOT / "tests"
BASELINE_PATH = REPO_ROOT / ".file-size-baseline.json"

SRC_LIMIT = 500
INTERNAL_LIMIT = 800
DATA_LIMIT = 1000
DATA_MODULES = frozenset({"models", "config", "enums", "protocols", "constants"})
TEST_LIMIT = 1000
WEB_LIMIT = 500
WEB_ROOT = REPO_ROOT / "web" / "src"


def _load_baseline() -> dict[str, int]:
    """Read the baseline file or return empty when missing.

    Returns:
        Mapping of ``<repo-relative path>`` to the maximum permitted line
        count for that file. Files absent from the mapping fall back to
        the category default (``SRC_LIMIT`` / ``TEST_LIMIT``).

    Raises:
        ValueError: When the baseline file is present but malformed.
    """
    if not BASELINE_PATH.exists():
        return {}
    raw = cast("dict[str, object]", json.loads(BASELINE_PATH.read_text(encoding="utf-8")))
    files_obj = raw.get("files")
    if not isinstance(files_obj, dict):
        msg = f"{BASELINE_PATH} 'files' key missing or not a mapping"
        raise ValueError(msg)
    out: dict[str, int] = {}
    for key, value in cast("dict[object, object]", files_obj).items():
        if not isinstance(key, str) or not isinstance(value, int):
            msg = f"{BASELINE_PATH} entry {key!r}: expected str -> int"
            raise ValueError(msg)
        out[key] = value
    return out


def _count_lines(path: Path) -> int:
    """Return the line count of ``path``."""
    with path.open("rb") as fh:
        return sum(1 for _ in fh)


def _python_files(root: Path) -> list[Path]:
    """Yield every ``*.py`` file under ``root`` excluding caches."""
    out: list[Path] = []
    if not root.exists():
        return out
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        out.append(path)
    return out


def src_limit(path: Path) -> int:
    """Return the line limit of a module under ``src/`` (tiers of ADR-015).

    Args:
        path: A Python file under ``src/now_workbench``.

    Returns:
        1000 for models/config/enums/protocols/constants, 800 under ``_internal/``, else 500.
    """
    if path.stem in DATA_MODULES or path.parent.name in DATA_MODULES:
        return DATA_LIMIT
    if "_internal" in path.parts:
        return INTERNAL_LIMIT
    return SRC_LIMIT


def _violation(path: Path, limit: int, baseline: dict[str, int]) -> str | None:
    """Return the violation for one file, honouring a grandfathered baseline size."""
    rel = path.relative_to(REPO_ROOT).as_posix()
    lines = _count_lines(path)
    baselined = baseline.get(rel)
    if baselined is not None:
        if lines > baselined:
            return f"{rel}: {lines} lines (baseline {baselined}, must not grow -- ADR-015)"
        return None
    if lines > limit:
        return (
            f"{rel}: {lines} lines exceeds limit of {limit} (ADR-015). Split the module; "
            f"a baseline entry in .file-size-baseline.json needs a justification."
        )
    return None


def _check(paths: list[Path], limit_of: Callable[[Path], int], baseline: dict[str, int]) -> list[str]:
    """Return human-readable violation strings for ``paths``."""
    found = (_violation(p, limit_of(p), baseline) for p in paths)
    return [v for v in found if v]


def _web_files() -> list[Path]:
    """Every TypeScript source of the web app (tests and declarations excluded)."""
    if not WEB_ROOT.exists():
        return []
    return [
        p for p in WEB_ROOT.rglob("*.ts") if not p.name.endswith((".d.ts", ".test.ts", ".spec.ts"))
    ]


def main() -> int:
    """Entry point; prints violations and returns a process exit code."""
    try:
        baseline = _load_baseline()
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"baseline error: {exc}", file=sys.stderr)
        return 2

    violations = (
        _check(_python_files(SRC_ROOT), src_limit, baseline)
        + _check(_python_files(TESTS_ROOT), lambda _p: TEST_LIMIT, baseline)
        + _check(_web_files(), lambda _p: WEB_LIMIT, baseline)
    )
    if not violations:
        return 0
    print("File-size violations (ADR-005 as amended by ADR-015):", file=sys.stderr)
    for v in violations:
        print(f"  {v}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
