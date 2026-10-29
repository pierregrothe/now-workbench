# Decision Log (ADRs)

Append-only record of architectural and design decisions for `now-workbench`.

---

### 2026-10-29 -- ADR-001: Hybrid Runtime with Python Core & Lit Web Components

**Status:** accepted

**Context:**
The ServiceNow SDK (`@servicenow/sdk`) is written in TypeScript and runs on Node.js.
However, for coding agents (Gemini Argon, Claude Opus) and rapid backend orchestration,
Python 3.14 with Pydantic v2 offers higher agentic velocity, cleaner schema validation,
and seamless integration with existing tools (like `nexus`). Furthermore, the UI must
replicate ServiceNow's modern Lux design language.

**Decision:**
1. Use **Python 3.14** for the core backend, CLI (Typer + Rich), and REST/WebSocket API (FastAPI).
2. Use **Lit Web Components** (TypeScript + Vite) for the frontend, mimicking ServiceNow's
   native Web Component architecture (`now-*`) and Lux design system.
3. Package both runtimes in a multi-stage Docker container so the user only runs a single
   container without worrying about Node or Python local installations.

**Consequences:**
- The Docker container bundles both Node.js (for `@servicenow/sdk`) and Python 3.14.
- The Python backend manages `now-sdk` execution via async streaming subprocesses.
- The frontend produces standard Web Components with zero framework lock-in.

---

### 2026-10-29 -- ADR-002: Otto AI Copilot via Claude API

**Status:** accepted

**Context:**
Users need an intelligent conversational assistant within the workbench to navigate demos,
troubleshoot `now-sdk` compile errors, explain Fluent code, and automate repetitive tasks.

**Decision:**
Integrate an embedded **Otto** copilot powered by the Anthropic Claude API (`anthropic` SDK).
The backend maintains an async WebSocket connection streaming Claude completions, with
injected context:
1. Current active demo bundle details.
2. Target ServiceNow instance version, status, and installed plugins.
3. Recent compiler/build error logs.

**Consequences:**
- User provides an `ANTHROPIC_API_KEY` (or passes it via environment / settings).
- Otto appears as a first-class drawer in the Lux UI with actionable chips.

---

### 2026-10-29 -- ADR-003: Declarative Demo Bundle Specification (`.sn-demo.zip`)

**Status:** accepted

**Context:**
Demonstration environments currently suffer from drift, missing seed data, and messy manual
deployment steps across diverse developer instances.

**Decision:**
Define a standardized `.sn-demo.zip` bundle specification:
- `manifest.json`: Bundle metadata, target ServiceNow version, dependencies.
- `fluent/`: ServiceNow Fluent TypeScript files (`*.now.ts`).
- `seed/`: Ordered JSON records for Table API insertion with tracked `sys_id`s for clean rollback.
- `properties/`: System property overrides.
- `walkthrough/`: Presenter guides and persona profiles.

**Consequences:**
- Demos become version-controlled, shareable, and fully reproducible with one-click teardown.

---

### 2026-10-29 -- ADR-004: Package Management Migration to uv + Hatchling

**Status:** accepted

**Context:**
Following the architecture pattern from `market-data-services`, Poetry has slower dependency
resolution and lock-file overhead. `uv` provides sub-second dependency installation, native
PEP 621 `[project]` / `[dependency-groups]` support, and seamless caching.

**Decision:**
1. Migrate from Poetry to `uv` with `hatchling` as the build backend.
2. Use standard `uv.lock` and PEP 621 `[project]` table in `pyproject.toml`.
3. Support local execution directly via `uv run workbench` and `uv run pytest`.

**Consequences:**
- Dependency resolution dropped from ~15s to ~700ms.
- Virtualenv activation is no longer required: commands can be invoked directly with `uv run`.
