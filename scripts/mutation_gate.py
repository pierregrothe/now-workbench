# scripts/mutation_gate.py
# Pre-push mutation gate: every mutant of the modules in [tool.mutmut] must be killed (ADR-029).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Run mutmut from a clean slate and fail on any mutant that is not killed.

The `mutants/` cache is deleted first: mutmut keeps a mutant's verdict while its function is
unchanged, so a weakened test would otherwise keep an old "killed". Any line `mutmut results`
prints (survived, timeout, suspicious, no tests, not checked) fails the gate.

A timeout is re-run once, alone: in fork-server mode mutmut forks each test process from a
process that runs a timer thread, and such a fork occasionally deadlocks, so under a full
parallel run a different, harmless mutant "times out" from run to run. Run alone, a real
hang still times out and fails; survivors are never retried.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

__all__ = ["main"]

ROOT = Path(__file__).resolve().parents[1]


def _mutmut(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "mutmut", *args], cwd=ROOT, env=env, capture_output=True, text=True, check=False
    )


def _not_killed(env: dict[str, str]) -> dict[str, str]:
    """Mutant name -> status, for every mutant `mutmut results` lists (none are killed)."""
    out = _mutmut(env, "results").stdout
    pairs = (line.strip().rsplit(": ", 1) for line in out.splitlines() if ": " in line)
    return {name: status for name, status in pairs}


def main() -> int:
    """Run the gate; return the process exit code."""
    shutil.rmtree(ROOT / "mutants", ignore_errors=True)
    # macOS refuses Objective-C initialisation after fork in the forkserver children.
    env = {**os.environ, "OBJC_DISABLE_INITIALIZE_FORK_SAFETY": "YES"}
    run = _mutmut(env, "run")
    left = _not_killed(env)
    timeouts = [name for name, status in left.items() if status == "timeout"]
    if run.returncode == 0 and timeouts:
        print(f"Re-running {len(timeouts)} timed-out mutants alone: {', '.join(timeouts)}")
        run = _mutmut(env, "run", *timeouts)
        left = _not_killed(env)
    if run.returncode != 0 or left:
        print(run.stdout[-2000:], run.stderr[-2000:], sep="\n", file=sys.stderr)
        print(f"Mutation gate FAILED: {len(left)} mutants not killed", file=sys.stderr)
        print("\n".join(f"{n}: {s}" for n, s in list(left.items())[:50]), file=sys.stderr)
        print("Inspect one with: uv run mutmut show <name>", file=sys.stderr)
        return 1
    print("Mutation gate passed: every mutant killed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
