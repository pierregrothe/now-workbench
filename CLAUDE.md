# now-workbench -- Project Instructions

## Project Summary

`now-workbench` is an AI-native developer and demonstration workbench for the ServiceNow
Fluent SDK (`@servicenow/sdk`). It unifies a Python 3.14 orchestrator, a ServiceNow Lux-styled
Web UI built with Lit Web Components, and an embedded Otto AI copilot powered by the Claude API.

## Primer Framework Context

This project strictly adheres to the **Primer** framework. Before making changes or planning epics:
- Review [`.primer/charter.md`](file:///.primer/charter.md) for project boundaries and goals.
- Review [`.primer/stack.md`](file:///.primer/stack.md) for allowed dependencies and runtimes.
- Review [`.primer/patterns.md`](file:///.primer/patterns.md) for strict architectural rules.
- Review [`.primer/active.md`](file:///.primer/active.md) for current focus and WIP.
- Review [`.primer/board.json`](file:///.primer/board.json) for epic/story definitions.

## Key Developer Commands (via uv)

```bash
# Run test suite
uv run pytest tests/

# Code quality & formatting
uv run ruff check .
uv run ruff format .
uv run mypy src

# CLI diagnostic & inspection
uv run workbench doctor
uv run workbench demo list
uv run workbench demo inspect sample-ai-assistant

# Start local server (FastAPI + Lux UI)
uv run workbench serve --host 127.0.0.1 --port 8080

# Frontend development (web/)
cd web && npm run dev
```

## Architectural Rules

1. **Python Runtime**: Python 3.14.10 strictly pinned (`.python-version`).
2. **Package Manager**: `uv` exclusively (no Poetry).
3. **No Mocks in Tests**: Use pure in-memory fakes (e.g. `NowSdkRunner(fake_mode=True)`).
4. **Pydantic v2**: Models must use strict type hints, frozen where applicable.
5. **UI Consistency**: Keep Lit Web Components aligned with ServiceNow Lux tokens in `web/src/styles/lux-theme.css`.
