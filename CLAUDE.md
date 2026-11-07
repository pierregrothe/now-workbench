# now-workbench -- Project Instructions

## Project Summary

`now-workbench` is an AI-native developer and demonstration workbench for the ServiceNow
Fluent SDK (`@servicenow/sdk`). It unifies a Python 3.14 orchestrator, a ServiceNow Lux-styled
Web UI built with Lit Web Components, and an embedded Otto AI copilot powered by the Claude API.

## Primer Framework Context

This project strictly adheres to the **Primer** framework. Before making changes or planning epics:
- Review [`.primer/charter.md`](file:///.primer/charter.md) for project boundaries and goals.
- Review [`.primer/governance.md`](file:///.primer/governance.md) for enforcement gates, ratchets, and policies.
- Review [`.primer/adr/ADR-005-constitutional-governance-and-3-tier-enforcement.md`](file:///.primer/adr/ADR-005-constitutional-governance-and-3-tier-enforcement.md) for constitutional invariants.
- Review [`.primer/stack.md`](file:///.primer/stack.md) for allowed dependencies and runtimes.
- Review [`.primer/patterns.md`](file:///.primer/patterns.md) for strict architectural rules.
- Review [`.primer/active.md`](file:///.primer/active.md) for current focus and WIP.
- Review [`.primer/board.json`](file:///.primer/board.json) for epic/story definitions.

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
   - `file-size`: File size caps (src <= 500 lines, `_internal` 800, models/config 1000; tests <= 1000; web <= 500; ADR-015, ADR-024).
   - `import-contracts`: Layer, acyclic-domain and public-root contracts (`lint-imports`, ADR-015).
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

# Ratchets, architecture contracts & Primer Governance
uv run python .ratchet/ratchet_check.py all
uv run lint-imports
uv run python .claude/scripts/primer-reconcile.py

# Pre-commit install & run
uv run pre-commit run --all-files

# CLI diagnostic & inspection
uv run workbench doctor
uv run workbench demo list
uv run workbench demo inspect sample-ai-assistant

# Start local server (FastAPI + Lux UI)
uv run workbench serve --host 127.0.0.1 --port 8080

# Frontend development (web/)
cd web && npm run dev

# End-to-end UI tests (Playwright on local Chrome, real backend; ADR-013)
cd web && npm run test:e2e
```

## Architectural Rules

1. **Python Runtime**: Python 3.14.10 strictly pinned (`.python-version`).
2. **Package Manager**: `uv` exclusively with `hatchling` backend (no Poetry).
3. **No Mocks in Tests**: Use pure in-memory fakes (e.g. `NowSdkRunner(fake_mode=True)`).
4. **Pydantic v2**: Models must use strict type hints, frozen where applicable (`extra="forbid"`).
5. **Subprocess Streaming**: Never use blocking `subprocess.run` in async code; stream lines via `asyncio.create_subprocess_exec`.
6. **Absolute Imports**: Always import from `now_workbench.<module>` (no relative `..` imports).
7. **UI Consistency**: Keep Lit Web Components aligned with ServiceNow Lux tokens in `web/src/styles/lux-theme.css`.
   Component CSS lives in a sibling `*-styles.ts`; read the store through `StoreController` (ADR-024).
8. **Layers (ADR-015)**: `interfaces -> domains -> platform`, never upward. Another package imports a
   domain only through `now_workbench.domains.<name>` (its `__init__`); add a name there to share it.
   Each domain owns its `<Name>Repository(conn)`; `db_session()` yields the connection. Checked by
   `uv run lint-imports` (`.importlinter`).

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
