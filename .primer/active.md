# now-workbench -- Active Work

Last updated: 2026-10-29
Branch: `main`
Python Version: `3.14.10`

## Current Focus

**Epic**: `EPIC-001: Foundation & Runtime Toolchain`
**Active Story**: `STORY-002: Implement NowSdkRunner async subprocess executor with log streaming`

### Completed Foundation:
1. Python 3.14.10 environment configured with `uv` and `hatchling` backend.
2. Demo bundle models and `BundleManager` implemented with export/import support.
3. Lit Web Components frontend scaffolded with ServiceNow Lux theme and Otto drawer.
4. FastAPI server with health checks, demo endpoints, and Otto WebSocket streaming.
5. Typer CLI (`workbench doctor`, `workbench demo list`, `workbench demo inspect`).
6. Initial starter demo bundle (`sample-ai-assistant`) created and verified.
7. Multi-stage `Dockerfile` and `docker-compose.yml` authored.
8. 100% passing tests (5/5), 0 Ruff linting violations, 0 Mypy strict errors.

## Next Steps

1. Wire real `now-sdk` local CLI subprocess execution into the WebSocket stream.
2. Expand Table API seed data injector for automatic transactional records loading.
3. Enhance Otto copilot with tool-calling capabilities (e.g. running builds or explaining tables directly from chat).
