# now-workbench -- Stack

## Runtime & Engines

- **Backend**: Python 3.14.10 (strictly pinned via `.python-version`)
- **Package Manager**: `uv` with `hatchling` backend (PEP 621 `[project]` specification)
- **ServiceNow SDK Runtime**: Node.js 20+ LTS with `@servicenow/sdk`
- **Frontend**: Lit 3.x (Web Components / TypeScript + Vite)
- **Database**: Embedded SQLite (STRICT tables, WAL, `foreign_keys=ON`), `PRAGMA user_version` migrations in `db/schema.py`, scoped `db_session` (ADR-006, ADR-012)
- **Containerization**: Multi-stage Docker image (Node.js build stage -> Python + Node runtime + uv)

## Layout

```text
now-workbench/
+-- .primer/                   # Primer framework context, registry, & ADRs
+-- .ratchet/                  # Metric ratchets and baselines.json
+-- src/now_workbench/         # Python application package (src layout)
|   +-- config/                # Pydantic v2 settings, paths, instance profiles
|   +-- db/                    # SQLite WAL session, models, and DatabaseRepository
|   +-- ai/                    # Claude API / Otto assistant integration (streaming + tools)
|   +-- sdk/                   # Async NowSdkRunner (spawns & streams @servicenow/sdk)
|   +-- bundles/               # Demo bundle manager (spec, pack, unpack, validate)
|   +-- seed/                  # ServiceNow Table API seed loader & rollback tracker
|   +-- templates/             # Customer parameterization & template instantiation engine
|   +-- runbooks/              # Guided presenter runbook parser & stage verifier
|   +-- properties/            # System property snapshotting, apply, restore, & reset
|   +-- fluent/                # Balanced-brace Fluent (*.now.ts) AST parser & diff engine
|   +-- capture/               # Playwright screenshot/video capture engine & playbook driver
|   +-- releases/              # Platform release hierarchy, min-version checks, workspace evolution
|   +-- plugins/               # ServiceNow instance plugin & module management
|   +-- synthesizer/           # Use-case-to-demo synthesizer engine & CLI
|   +-- instances/             # Instance registry CLI (`workbench instance ...`)
|   +-- api/                   # FastAPI routes (demos, instances, templates, threads) & WS
|   +-- remediation.py         # Automated toolchain & environment doctor --fix engine
|   +-- cli.py                 # Typer CLI entrypoint (`workbench`)
+-- web/                       # Lit Web Components frontend (Lux + Otto)
|   +-- src/
|   |   +-- styles/lux-theme.css # ServiceNow Lux design tokens & variables
|   |   +-- components/        # <now-workbench-shell>, <now-fluent-explorer>, etc.
|   |   +-- main.ts
|   +-- package.json
|   +-- tsconfig.json
|   +-- vite.config.ts
+-- tests/                     # Deterministic in-memory test suite (100% coverage)
+-- Dockerfile                 # Multi-stage portable container
+-- docker-compose.yml
+-- pyproject.toml             # Standard PEP 621 project table managed by uv
```

## Core Dependencies

### Python
- `fastapi >= 0.115` -- High-performance async REST & WebSocket server
- `uvicorn[standard] >= 0.32` -- ASGI production server
- `typer >= 0.13` -- Modern CLI framework with Rich formatting
- `rich >= 13.9` -- Terminal tables & panels
- `pydantic >= 2.9` -- Strict schemas (`frozen=True`, `extra="forbid"`)
- `pydantic-settings >= 2.6` -- Configuration from environment & `.env`
- `httpx >= 0.28` -- Async/sync HTTP client for ServiceNow Table API & Claude API
- `anthropic >= 0.40` -- Anthropic Claude Python SDK (Otto copilot)
- `cryptography >= 46` -- AES-256-GCM sealing of instance credentials and API key (ADR-012)
- `pyjwt[crypto]` -- verifies Cloudflare Access tokens (ADR-016)

### Frontend (web/)
- `lit >= 3.2` -- Open-standard Web Components library
- `vite >= 5.4` -- Frontend bundler
- `typescript >= 5.6` -- Strict TypeScript (`noEmit: true`)
- `@playwright/test >= 1.65` (dev) -- End-to-end UI tests on local Chrome against the real backend (ADR-013)
- `@types/node` (dev) -- Node typings for Playwright fixtures that seed state via the Python repository

## Dev Tools & Code Quality
- `pytest >= 8.3` with `pytest-asyncio` and `pytest-cov` (100% coverage floor)
- `ruff >= 0.8` (linting & formatting, 0 violations, line length 100)
- `mypy >= 1.13` (strict mode, 0 errors)
