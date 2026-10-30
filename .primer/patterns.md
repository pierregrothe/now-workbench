# now-workbench -- Architectural Patterns & Conventions

## 1. Python Architecture & Coding Standards

- **Strict Type Hints**: Full type annotations everywhere.
  `mypy` strict mode with 0 errors required.
- **Pydantic v2 Models**:
  - Use `BaseModel` with explicit field definitions and docstrings.
  - Strict input validation for manifests, profiles, and API payloads.
- **Pure Fakes Over Mocks**:
  - Never use `unittest.mock.patch` or monkey-patching in tests.
  - Use deterministic in-memory fakes (e.g. `NowSdkRunner(fake_mode=True)`).
- **Subprocess & Stream Safety**:
  - Never invoke blocking `subprocess.run` inside async code.
  - Always use `asyncio.create_subprocess_exec` with line-by-line streaming.
- **Absolute Imports**:
  - Always import from `now_workbench.<module>` (no relative `..` imports).
- **Package Management**:
  - `uv` is the standard tool. All developer commands use `uv run <command>`.

## 2. Frontend (Lit Web Components) Standards

- **Shadow DOM Encapsulation**:
  - Component styles encapsulated inside `static styles = css`\`...\`\`.
  - Global theme variables inherited via `:host` and CSS custom properties (`--now-*`).
- **ServiceNow Lux Styling**:
  - Surfaces: `--now-bg-canvas` (#0c1014), `--now-bg-surface-0` (#13171d), `--now-bg-surface-1` (#1a2027).
  - Accents: Teal (`#2bd2b5`), Luminous Otto Purple (`#a855f7`).
  - Subtle borders: `rgba(255, 255, 255, 0.08)`.
- **Event-Driven Component Decoupling**:
  - Child components dispatch typed custom events (`demo-deploy`, `otto-prompt`, `tab-change`).
  - Root shell orchestrates state and backend API communications.

## 3. Demo Bundle Specification

- Standard `.sn-demo.zip` structure:
  - `manifest.json`: Root metadata (`id`, `name`, `version`, `sn_release`, `personas`, `tags`).
  - `fluent/`: ServiceNow Fluent TypeScript source (`*.now.ts`).
  - `seed/`: Sequenced JSON files for Table API insertion.
  - `properties/`: Key-value system property overrides.
  - `walkthrough/`: Presenter script (`guide.md`) and persona details.

## 4. Governance & 3-Tier Enforcement (ADR-005)

- **Tier 1 (Blocking)**: `ruff`, `ruff-format`, `mypy`, `pytest`, `file-size`, `conventional-pre-commit`, and `primer-reconcile`.
- **Tier 2 (Ratchets in `.ratchet/`)**: Baselines in `baselines.json` can only improve, never regress (`no-mocks`, `complexity`, `file-size`, `type-ignores`, `absolute-imports`).
- **Tier 3 (Soft)**: Advisory walkthrough and bundle documentation reminders.
- **ASCII-Only**: Inviolable requirement across code, tests, docs, and git commit messages.
- **Domain Boundaries**: No unrelated domain rules (financial, trading) allowed.

