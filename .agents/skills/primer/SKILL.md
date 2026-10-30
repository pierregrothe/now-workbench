---
name: primer
description: >-
  Primer project governance, ADR management, roadmap tracking, and policy drift
  reconciliation. Use whenever the user invokes /primer commands (such as /primer sync,
  /primer init, /primer status, /primer story start, /primer story done, /primer reconcile,
  /primer brainstorm, /primer epic, /primer prd add) or asks to govern, track, and reconcile.
---

# Primer Project Governance & Lifecycle Skill

This skill provides full support for the **Primer** framework in Antigravity, enabling
autonomous and interactive execution of all `/primer` workflows.

## Available Slash Workflows

### 1. `/primer status`
Inspect active focus, story progress, and epic completion.
- Inspects [`.primer/active.md`](file:///.primer/active.md) and [`.primer/board.json`](file:///.primer/board.json).
- Checks test suite and ratchet status.

### 2. `/primer sync`
Synchronize governance, reconcile policy drift, and verify gates before commits or PRs:
- Runs `uv run python .claude/scripts/primer-reconcile.py`
- Runs `uv run python .ratchet/ratchet_check.py all`
- Verifies zero drift between ADRs, hooks, and [`.primer/policies/registry.yaml`](file:///.primer/policies/registry.yaml).

### 3. `/primer init`
Initialize or bootstrap Primer structure:
- Scaffolds `.primer/` with `charter.md`, `board.json`, `active.md`, `progress.md`, and `policies/registry.yaml`.

### 4. `/primer story start <slug_or_id>`
Transition a story to in-progress before code edits:
- Updates story status to `"in_progress"` in [`.primer/board.json`](file:///.primer/board.json).
- Updates [`.primer/active.md`](file:///.primer/active.md) with active focus.

### 5. `/primer story done <slug_or_id>`
Mark a story as completed:
- Verifies tests and acceptance criteria.
- Updates story status to `"done"` in [`.primer/board.json`](file:///.primer/board.json).
- If all stories in the epic are completed, marks the epic as `"done"`.
- Updates [`.primer/progress.md`](file:///.primer/progress.md).

### 6. `/primer reconcile`
Validate policies and reconcile governance drift:
```bash
uv run python .claude/scripts/primer-reconcile.py
```

### 7. `/primer brainstorm` / `/primer epic`
Decompose ideas into epics and stories:
- Documents architectural decisions in `.primer/brainstorming/` and `.primer/adr/`.
- Appends newly structured epics and stories into [`.primer/board.json`](file:///.primer/board.json).

## Automated Helper Script

Use the helper script to run operations directly:
```bash
python .agents/skills/primer/scripts/primer_runner.py status
python .agents/skills/primer/scripts/primer_runner.py story-start STORY-005
python .agents/skills/primer/scripts/primer_runner.py story-done STORY-005
python .agents/skills/primer/scripts/primer_runner.py sync
```
