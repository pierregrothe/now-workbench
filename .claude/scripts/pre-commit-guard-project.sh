#!/bin/bash
# .claude/scripts/pre-commit-guard-project.sh
# PreToolUse commit guard for now-workbench (ADR-005).
# Author: Pierre Grothe
# Date: 2026-10-29

STAGED=$(git diff --cached --name-only 2>/dev/null || true)
SRC_CHANGED=$(echo "$STAGED" | grep -E "^src/|^tests/" || true)
PRIMER_CHANGED=$(echo "$STAGED" | grep "^\.primer/" || true)

if [ -n "$SRC_CHANGED" ] && [ -z "$PRIMER_CHANGED" ]; then
    echo "[NOTICE] src/ or tests/ modified without .primer/ updates -- consider syncing .primer/" >&2
fi
exit 0
