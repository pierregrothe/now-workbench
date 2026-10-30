#!/usr/bin/env python3
# .agents/scripts/session_start.py
# Antigravity SessionStart hook for now-workbench.
# Author: Pierre Grothe
# Date: 2026-10-29
"""Inject Primer context and constitutional rules at session start."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    try:
        # Read incoming payload
        _ = json.load(sys.stdin)
    except Exception:
        pass

    message = (
        "Antigravity Primer Governance active for `now-workbench`.\n"
        "- Constitutional ADR: ADR-005 (In-memory fakes only, Python 3.14 + uv, "
        "Pydantic v2, Lux styling, absolute imports).\n"
        "- Net-increase ratchets: .ratchet/baselines.json\n"
        "- Local drift reconciliation: .claude/scripts/primer-reconcile.py\n"
        "All governance runs locally in Antigravity and git pre-commit hooks."
    )

    out = {"injectSteps": [{"systemMessage": {"systemMessage": message}}]}
    sys.stdout.write(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
