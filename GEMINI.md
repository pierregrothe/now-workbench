# now-workbench -- Project Instructions (Antigravity & Claude Code)

## Project Summary

`now-workbench` is an AI-native developer and demonstration workbench for the ServiceNow
Fluent SDK (`@servicenow/sdk`). It unifies a Python 3.14 orchestrator, a ServiceNow Lux-styled
Web UI built with Lit Web Components, and an embedded Otto AI copilot powered by the Claude API.

- **Python**: 3.14.10 strictly pinned (`.python-version`)
- **Package Manager**: `uv` exclusively with `hatchling` backend (PEP 621)
- **Frontend**: Lit 3.x Web Components with ServiceNow Lux design tokens
- **Enforcement**: 100% local hooks and ratchets -- **no GitHub Actions CI dependency**

## Primer Framework Context

This project strictly adheres to the **Primer** framework:
- [`.primer/charter.md`](file:///.primer/charter.md): Project boundaries, vision, and core capabilities.
- [`.primer/governance.md`](file:///.primer/governance.md): Enforcement gates, ratchets, and policy mapping.
- [`.primer/adr/ADR-005-constitutional-governance-and-3-tier-enforcement.md`](file:///.primer/adr/ADR-005-constitutional-governance-and-3-tier-enforcement.md): Constitutional invariants and 3-tier enforcement model.
- [`.primer/patterns.md`](file:///.primer/patterns.md): Architectural patterns and conventions.
- [`.primer/stack.md`](file:///.primer/stack.md): Allowed runtimes, dependencies, and layout.
- [`.primer/active.md`](file:///.primer/active.md): Current focus, active story, and WIP.
- [`.primer/board.json`](file:///.primer/board.json): Epics and stories.

## Constitutional Requirements (ADR-005)

Non-negotiable constitutional rules for `now-workbench`:
1. **Python 3.14.10 & uv**: Python 3.14.10 runtime pinned via `.python-version`; `uv` is the sole package manager.
2. **In-Memory Fakes Over Mocks**: All tests must use pure in-memory fakes (`NowSdkRunner(fake_mode=True)`). Never use `unittest.mock` or monkey-patching.
3. **Pydantic v2 Integrity**: Models use strict type hints, `frozen=True` where applicable, and `extra="forbid"`.
4. **Subprocess & Stream Safety**: Never invoke blocking `subprocess.run` inside async code. Always use `asyncio.create_subprocess_exec` with streaming stdout/stderr.
5. **Absolute Imports**: Always import from `now_workbench.<module>` (no relative `..` imports).
6. **Frontend Encapsulation**: Lit Web Components encapsulated via Shadow DOM using ServiceNow Lux CSS tokens (`--now-*`).
7. **Declarative Demo Bundles**: Self-contained `.sn-demo.zip` format with Fluent source, seed data, properties, and guides.
8. **ASCII-Only Codebase**: All source files, tests, documentation, and commit messages must use ASCII-only characters (0x00-0x7F).
9. **No Unrelated Domain Rules**: Governance is strictly scoped to `now-workbench` (zero financial market/trading data rules).

## Local Enforcement & Hook Architecture

All gates run **locally** at specific development milestones. No external GitHub Actions CI is required.

1. **Per-Edit Feedback**:
   - `scripts/dev-tools/per_edit_check.py`: Evaluates modified Python files immediately after tool write/edit.
   - Claude Code: Configured via `.claude/settings.json` (`PostToolUse`).
   - Antigravity: Configured via `.agents/hooks.json` (`PreToolUse`, `PostToolUse`, `Stop`).
2. **Pre-Commit Gates**:
   - `ruff`: Fast Python linting (0 violations).
   - `ruff-format`: Formatting check across all Python files.
   - `mypy`: Strict static type checking on `src/`.
   - `file-size`: File size caps (src <= 800 lines, tests <= 1000 lines).
   - `ratchet-all`: Evaluates metric ratchets in `.ratchet/` (violations can only decrease, never increase).
   - `primer-reconcile`: Validates `.primer/policies/registry.yaml` against live hooks and ADR files.
   - `conventional-pre-commit`: Conventional Commits message validation (`commit-msg` stage).
3. **Pre-Push Gate**:
   - `pytest-pre-push`: Full test suite pass using deterministic in-memory fakes before any code is pushed.

## Key Developer Commands (via uv)

```bash
# Run test suite
uv run pytest tests/

# Code quality & formatting
uv run ruff check .
uv run ruff format --check .
uv run mypy src

# Ratchets & Primer Governance
uv run python .ratchet/ratchet_check.py all
uv run python .claude/scripts/primer-reconcile.py

# Pre-commit install & run
uv run pre-commit install --install-hooks
uv run pre-commit install --hook-type commit-msg
uv run pre-commit install --hook-type pre-push
uv run pre-commit run --all-files

# Workbench CLI diagnostics
uv run workbench doctor
uv run workbench demo list
uv run workbench demo inspect sample-ai-assistant

# Start local server (FastAPI + Lux UI)
uv run workbench serve --host 127.0.0.1 --port 8080

# Frontend development (web/)
cd web && npm run dev
```

<!-- primer:triggers:start (managed by /primer bootstrap -- edit outside the markers) -->
## Primer Workflow Triggers

RUN these yourself (evidence-based bookkeeping):
- `/primer story start <slug>` -- the moment you begin implementing a
  roadmap/epic item, BEFORE the first code edit.
- `/primer story done <slug>` -- every AC / Tasks / DoD checkbox is
  checked and the work is merged.
- `/primer status` -- on any staleness nudge, or before starting new work.
- `/primer sync` -- at post-merge / pre-PR boundaries (lease rules apply).

SUGGEST these, never auto-run (product decisions stay human):
- `/primer brainstorm` -- a substantial new idea has no epic or spec
  behind it yet.
- `/primer epic` -- an approved brainstorm or roadmap phase needs story
  decomposition.
- `/primer prd add` -- a product-level commitment is being made (charter
  required; suggest `/primer charter` first if it is missing).
- `/primer roadmap` / `governance` / `charter` -- the file is missing or
  the user asks to plan or govern.
- `/primer reconcile` -- the commit gate blocks (exit 2) or status shows
  registry drift.
- `/primer upgrade` -- status reports Roadmap Aging or cleanup candidates.
<!-- primer:triggers:end -->
