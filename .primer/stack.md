# now-workbench -- Stack

## Runtime & Engines

- **Backend**: Python 3.14 (compatible with 3.12+)
- **Package Manager**: `uv` with `hatchling` backend (PEP 621 `[project]` specification)
- **ServiceNow SDK Runtime**: Node.js 20+ LTS with `@servicenow/sdk`
- **Frontend**: Lit 3.x (Web Components / TypeScript + Vite)
- **Containerization**: Multi-stage Docker image (Node.js build stage -> Python + Node runtime + uv)

## Layout

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
│   ├── test_api.py
│   ├── test_bundles.py
│   └── test_sdk_runner.py
├── Dockerfile                 # Multi-stage portable container
├── docker-compose.yml
└── pyproject.toml             # Standard PEP 621 project table managed by uv
```

## Core Dependencies

### Python
- `fastapi >= 0.115` -- High-performance async REST & WebSocket server
- `uvicorn[standard] >= 0.32` -- ASGI production server
- `typer >= 0.13` -- Modern CLI framework with Rich formatting
- `rich >= 13.9` -- Beautiful terminal tables & panels
- `pydantic >= 2.9` -- Strict schemas (`frozen=True`, `extra="forbid"`)
- `pydantic-settings >= 2.6` -- Configuration from environment & YAML
- `httpx >= 0.28` -- Async HTTP client for ServiceNow REST & Claude API
- `anthropic >= 0.40` -- Anthropic Claude Python SDK (Otto copilot)

### Frontend (web/)
- `lit >= 3.2` -- Open-standard Web Components library
- `vite >= 5.4` -- Next-generation frontend tooling
- `typescript >= 5.6` -- Strict TypeScript

## Dev Tools & Code Quality
- `pytest >= 8.3` with `pytest-asyncio` and `pytest-cov`
- `ruff >= 0.8` (linting & formatting, 0 violations)
- `mypy >= 1.13` (strict mode, 0 errors)
- `black >= 24.10` (line length 100)
