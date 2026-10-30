#!/usr/bin/env python3
# .ratchet/ratchet_check.py
# Count-ratchet enforcement: violations can decrease but never increase.
# Author: Pierre Grothe
# Date: 2026-10-29
"""Count-ratchet enforcement for now-workbench.

Runs a validator, counts violations, compares against a stored baseline.
If violations increased, the check FAILS (blocks the commit). If violations
decreased, hook-invoked runs REPORT the improvement without persisting it;
tightening the committed baseline is performed via the explicit `tighten` subcommand.

Usage:
    python .ratchet/ratchet_check.py all            # Run all validators in parallel pool
    python .ratchet/ratchet_check.py <name>         # Run a single validator
    python .ratchet/ratchet_check.py tighten        # Persist improved baselines
    python .ratchet/ratchet_check.py tighten <name> # Persist one validator's baseline
    python .ratchet/ratchet_check.py --init         # Initialize baseline values
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

RATCHET_DIR = Path(__file__).parent
BASELINES_FILE = RATCHET_DIR / "baselines.json"
REPO_ROOT = RATCHET_DIR.parent

VALIDATORS = {
    "no-mocks": {
        "cmd": [sys.executable, str(RATCHET_DIR / "count_no_mocks.py")],
        "description": "ADR-005 in-memory fakes only (no unittest.mock)",
    },
    "complexity": {
        "cmd": [sys.executable, str(RATCHET_DIR / "count_complexity.py")],
        "description": "ADR-005 function complexity <= 10",
    },
    "file-size": {
        "cmd": [sys.executable, str(RATCHET_DIR / "count_file_size.py")],
        "description": "ADR-005 file size limits (src <= 800, tests <= 1000)",
    },
    "type-ignores": {
        "cmd": [sys.executable, str(RATCHET_DIR / "count_type_ignores.py")],
        "description": "ADR-005 type: ignore burndown ratchet",
    },
    "absolute-imports": {
        "cmd": [sys.executable, str(RATCHET_DIR / "count_absolute_imports.py")],
        "description": "ADR-005 absolute imports in src/ (no relative imports)",
    },
    "ascii-only": {
        "cmd": [sys.executable, str(RATCHET_DIR / "count_ascii_only.py")],
        "description": "ADR-005 ASCII-only codebase (0x00-0x7F)",
    },
    "pydantic-strict": {
        "cmd": [sys.executable, str(RATCHET_DIR / "count_pydantic_strict.py")],
        "description": "ADR-005 strict frozen Pydantic v2 models",
    },
    "async-subprocess": {
        "cmd": [sys.executable, str(RATCHET_DIR / "count_async_subprocess.py")],
        "description": "ADR-005 non-blocking async subprocess execution",
    },
}


class ValidatorCrashedError(RuntimeError):
    """A validator exited non-zero without printing a violation count."""


def _load_baselines() -> dict[str, int]:
    """Load baseline violation counts."""
    if BASELINES_FILE.exists():
        try:
            data = json.loads(BASELINES_FILE.read_text(encoding="utf-8"))
            return data.get("counts", {})
        except Exception:
            return {}
    return {}


def _save_baselines(counts: dict[str, int]) -> None:
    """Save baseline violation counts."""
    data = {
        "updated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "counts": counts,
    }
    BASELINES_FILE.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )


def _count_violations(cmd: list[str]) -> int:
    """Run a validator command and extract the violation count."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=False,
    )
    output = result.stdout + result.stderr

    for line in output.splitlines():
        if "Violations:" in line:
            m = re.search(r"Violations:\s*(\d+)", line)
            if m:
                return int(m.group(1))

    # Fallback to line counting error patterns
    count = 0
    counted = False
    for line in output.splitlines():
        if line.startswith(("[ERROR]", "[WARN]")):
            count += 1
            counted = True

    if result.returncode != 0 and not counted:
        raise ValidatorCrashedError(f"Command {' '.join(cmd)} failed with exit {result.returncode}")

    return count


def check_validator(name: str, write: bool = False) -> tuple[bool, int, int]:
    """Run check for one validator. Returns (passed, current, baseline)."""
    if name not in VALIDATORS:
        print(f"Unknown validator: {name}", file=sys.stderr)
        return False, 0, 0

    val = VALIDATORS[name]
    baselines = _load_baselines()
    baseline = baselines.get(name, 999999)

    current = _count_violations(val["cmd"])

    if current > baseline:
        print(
            f"RATCHET FAIL: {name} ({val['description']})\n"
            f"  Current violations: {current} > Baseline: {baseline} (regressed!)",
            file=sys.stderr,
        )
        return False, current, baseline

    if current < baseline:
        print(
            f"RATCHET IMPROVEMENT: {name} ({val['description']})\n"
            f"  Current violations: {current} < Baseline: {baseline} (can tighten!)"
        )
        if write:
            baselines[name] = current
            _save_baselines(baselines)
            print(f"  Tightened baseline to {current}.")
    else:
        print(f"RATCHET OK: {name} ({current}/{baseline})")

    return True, current, baseline


def run_all(write: bool = False) -> int:
    """Run all validators in parallel pool when read-only, or sequentially when tightening."""
    if write:
        failed = False
        for name in VALIDATORS:
            passed, _, _ = check_validator(name, write=True)
            if not passed:
                failed = True
        return 1 if failed else 0

    names = list(VALIDATORS.keys())
    with ThreadPoolExecutor(max_workers=len(names)) as pool:
        results = list(pool.map(lambda n: check_validator(n, write=False), names))
    return 1 if any(not passed for passed, _, _ in results) else 0


def init_baselines() -> int:
    """Initialize baselines from current measurements."""
    counts = {}
    for name, val in VALIDATORS.items():
        count = _count_violations(val["cmd"])
        counts[name] = count
        print(f"Initialized {name}: {count}")
    _save_baselines(counts)
    print(f"Saved initial baselines to {BASELINES_FILE}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: ratchet_check.py [all | <name> | tighten | tighten <name> | --init]")
        return 1

    arg = sys.argv[1]
    if arg == "--init":
        return init_baselines()
    if arg == "all":
        return run_all(write=False)
    if arg == "tighten":
        if len(sys.argv) > 2:
            target = sys.argv[2]
            passed, _, _ = check_validator(target, write=True)
            return 0 if passed else 1
        return run_all(write=True)
    if arg in VALIDATORS:
        passed, _, _ = check_validator(arg, write=False)
        return 0 if passed else 1

    print(f"Unknown argument: {arg}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
