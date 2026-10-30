# ADR-005: Constitutional Governance and 3-Tier Enforcement Model

**Status:** accepted
**Date:** 2026-10-29

## Context

`now-workbench` is an AI-native developer and demonstration workbench for the ServiceNow
Fluent SDK (`@servicenow/sdk`). It integrates a Python 3.14 orchestrator, a Lit Web
Components frontend matching ServiceNow Lux styling, and an embedded Otto AI copilot.

As development proceeds with multiple AI coding agents and human contributors, the
codebase requires rigorous, automated governance to prevent architectural drift, ensure
100% test determinism, preserve strict typing, and maintain fidelity to the ServiceNow
Lux design language.

A single-tier enforcement model ("block or ignore") creates friction or silent failures.
`now-workbench` adopts Primer's 3-Tier Enforcement Model (Blocking, Ratchet, Soft) to
guarantee that quality and compliance can only improve over time, never regress.

## Decision

### 1. 3-Tier Enforcement Architecture

1. **Tier 1 -- Blocking Gates (Pre-commit & CI)**:
   - Invariants that run on staged files and block commits or CI merges immediately on failure.
   - Zero tolerance for violations.
   - Core gates:
     - `ruff`: Python linting (0 violations; bans bare excepts, relative imports, and dead code).
     - `ruff-format`: Fast code formatting check across all Python files.
     - `mypy`: Strict static type checking on `src/` (0 errors, 100% type coverage).
     - `web-typecheck`: Strict TypeScript compiler check (`tsc --noEmit`) on `web/src/`.
     - `pytest-pre-push`: Full test suite pass using deterministic in-memory fakes with 100% coverage floor (`--cov-fail-under=100`).
     - `file-size`: File size limits (src/ <= 800 lines, tests/ <= 1000 lines).
     - `conventional-pre-commit`: Conventional Commits message format (`feat:`, `fix:`, `chore:`, etc.).
     - `primer-reconcile`: Standing drift detection between `.primer/policies/registry.yaml`, git hooks, and `.primer/governance.md`.

2. **Tier 2 -- Ratchet Enforcement (`.ratchet/`)**:
   - Baseline-tracked numeric metrics stored in `.ratchet/baselines.json` and executed in parallel via `ThreadPoolExecutor`.
   - Violations can decrease (burndown) or stay equal, but can never increase.
   - Net-new violations fail the pre-commit check (`ratchet-all`).
   - Core validators:
     - `no-mocks`: Count of `unittest.mock` / `pytest-mock` occurrences in tests must remain 0.
     - `complexity`: Count of functions with cyclomatic/cognitive complexity > 10 must remain <= baseline.
     - `file-size`: Grandfathered oversize files cannot grow beyond baseline.
     - `type-ignores`: Count of `# type: ignore` comments in `src/` must remain <= baseline.
     - `absolute-imports`: Count of relative imports (`from .` or `from ..`) must remain 0.
     - `ascii-only`: Count of non-ASCII files across `src/`, `tests/`, `web/src/`, and `.primer/` must remain 0.
     - `pydantic-strict`: Count of `BaseModel` subclasses in `src/` missing `ConfigDict(extra="forbid", frozen=True)` must remain 0.
     - `async-subprocess`: Count of blocking `subprocess.run` calls inside `async def` functions in `src/` must remain 0.

3. **Tier 3 -- Soft / Advisory Gates**:
   - Informational notices that advise developers and agents without blocking iteration.
   - Includes manifest schema hints and demo walkthrough completeness warnings.

### 2. Constitutional Invariants for now-workbench

The following rules apply to all code in `now-workbench` and cannot be weakened:

1. **Python 3.14.10 & uv**: Python 3.14.10 runtime strictly pinned in `.python-version`; `uv` with `hatchling` backend is the sole package manager (PEP 621 `pyproject.toml`).
2. **In-Memory Fakes Over Mocks**: All tests must use deterministic in-memory fakes (e.g. `NowSdkRunner(fake_mode=True)`). No monkey-patching or `unittest.mock`.
3. **Pydantic v2 Models**: All domain models (`DemoManifest`, `DemoBundleInfo`, `InstanceRecord`, `TemplateRecord`, `ChatThreadRecord`, `ChatMessageRecord`, `SeedOperationRecord`, `SdkExecutionResult`) must use strict Pydantic v2 schemas (`extra="forbid"`, `frozen=True`, complete type annotations).
4. **Subprocess & Async Safety**: Never invoke blocking `subprocess.run` inside async code paths. Always use `asyncio.create_subprocess_exec` with streaming stdout/stderr.
5. **Absolute Imports**: Always import from `now_workbench.<module>` (no relative imports).
6. **Frontend Encapsulation & ServiceNow Lux Tokens**: Lit Web Components must use Shadow DOM encapsulation and consume ServiceNow Lux CSS custom properties (`--now-*`).
7. **Declarative Demo Bundles**: Demonstrations are packaged as self-contained `.sn-demo.zip` archives with Fluent TypeScript, Table API seed records, system properties, and walkthrough guides.
8. **Character Hygiene**: All Python source code, tests, markdown documentation, and commit messages must use ASCII-only characters (0x00-0x7F).

### 3. Domain Rule Boundaries

This project strictly avoids importing rules or constraints from unrelated domains (such as financial market data, trading calendars, or external accounting precision). All governance rules must directly serve the operation and maintenance of `now-workbench`.

## Consequences

- All code committed locally is validated by pre-commit hooks and count ratchets before reaching remote repositories.
- Code quality, type safety, and test suite health can only improve or remain constant.
- Automated tools (`primer-reconcile`) prevent divergence between policy documentation and live git configuration.
