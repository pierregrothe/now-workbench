#!/usr/bin/env python3
# .agents/scripts/pre_invocation.py
# Antigravity PreInvocation hook for now-workbench.
# Author: Pierre Grothe
# Date: 2026-10-29
"""Inject ephemeral rule reminders before model invocation."""

from __future__ import annotations

import json
import sys


def main() -> int:
    try:
        _ = json.load(sys.stdin)
    except Exception:
        pass

    reminder = (
        "Primer Guardrails (ADR-005): In-memory fakes only (zero mocks) | "
        "Python 3.14 + uv | Strict Pydantic v2 | Shadow DOM Lux CSS | Absolute imports | ASCII only"
    )

    out = {"injectSteps": [{"ephemeralMessage": reminder}]}
    sys.stdout.write(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
