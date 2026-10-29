# now-workbench -- Stack

## Runtime & Engines

- **Backend**: Python 3.14 (compatible with 3.12+)
- **ServiceNow SDK Runtime**: Node.js 20+ LTS with `@servicenow/sdk`
- **Frontend**: Lit 3.x (Web Components / TypeScript + Vite)
- **Containerization**: Multi-stage Docker image (Node.js build stage -> Python + Node runtime)

## Package Management

- Python: Poetry (`pyproject.toml`) with in-project virtualenv (`.venv`).
- Frontend: npm / package.json in `web/`.

## Architecture & Layout

```text
now-workbench/
├── .primer/                   # Primer framework context & ADRs
├── src/now_workbench/         # Python application package (src layout)
│   ├── config/                # Pydantic v2 settings, paths, instance profiles
│   ├── ai/                    # Claude API / Otto assistant integration (streaming + tools)
│   ├── sdk/                   # Async NowSdkRunner (spawns & streams @servicenow/sdk)
│   ├── bundles/               # Demo bundle manager (spec, pack, unpack, validate)
│   ├── seed/                  # ServiceNow Table API seed loader & rollback tracker
│   ├── api/                   # FastAPI routes & WebSocket handlers (/ws/stream, /ws/otto)
│   └── cli.py                 # Typer CLI entrypoint (`workbench`)
├── web/                       # Lit Web Components frontend (Lux + Otto)
│   ├── src/
│   │   ├── styles/lux-theme.css # ServiceNow Lux design tokens & variables
│   │   ├── components/        # <now-workbench-shell>, <now-nav-rail>, <now-otto-drawer>, etc.
│   │   └── main.ts
│   ├── package.json
│   └── vite.config.ts
├── tests/                     # Unit and integration test suite
│   ├── fakes/                 # In-memory fakes for SDK runner & ServiceNow Table API
│   └── ...
├── Dockerfile                 # Multi-stage portable container
└── docker-compose.yml
```

## Core Dependencies

### Python
- `fastapi >= 0.115` -- High-performance async REST & WebSocket server
- `uvicorn[standard] >= 0.32` -- ASGI production server
- `typer[all] >= 0.13` -- Modern CLI framework with Rich formatting
- `pydantic >= 2.9` -- Strict schemas (`frozen=True`, `extra="forbid"`)
- `pydantic-settings >= 2.6` -- Configuration from environment & YAML
- `httpx >= 0.28` -- Async HTTP client for ServiceNow REST & Claude API
- `anthropic >= 0.40` -- Anthropic Claude Python SDK (Otto copilot)

### Frontend (web/)
- `lit >= 3.2` -- Open-standard Web Components library
- `vite >= 5.4` -- Next-generation frontend tooling
- `typescript >= 5.6` -- Strict TypeScript

## Dev Tools & Code Quality
- `pytest >= 9.0` with `pytest-asyncio` and `pytest-cov`
- `ruff >= 0.15` (linting & formatting, 0 violations)
- `mypy >= 1.0` (strict mode, 0 errors)
- `black >= 26.0` (line length 100)
