# ADR-013: Playwright End-to-End UI Testing Against the Real Backend

**Status:** accepted
**Date:** 2026-11-06

## Context

The Lit/Lux frontend had no automated tests. Only `tsc --noEmit` (ADR-001) guarded it,
which proves types, not behavior.

On 2026-11-06 the owner found a ServiceNow instance (`demoalectriallwfau164179`) in the
admin panel, even though the database held none:
- `now-admin-panel.ts` started from a hardcoded `DEFAULT_SAMPLE_INSTANCES` list, with the
  fake entry marked "authenticated".
- It kept that list whenever `/api/instances` returned an empty array.

Python unit tests could not catch this: the backend was correct, and the defect existed
only in what the browser rendered. This is the same "silent fake fallback" that ADR-011
forbids for the AI path.

## Decision

1. **Tool:** `@playwright/test` (dev dependency in `web/`). It runs against the locally
   installed Google Chrome (`channel: 'chrome'`), so no browser binaries are downloaded.
   Chromium-only is acceptable: the workbench is a Chrome-targeted local tool, and the
   capture pipeline already requires Chrome.
2. **Real backend, no API mocking.** Playwright's `webServer` runs these steps from the
   repo root:
   - delete `.e2e/` (fresh state every run);
   - build the UI into `.e2e/dist` (never `web/dist`, which `workbench serve` uses);
   - start `uv run workbench serve` on port 8091, with an isolated `WORKBENCH_DATA_DIR`
     and `WORKBENCH_KEY_FILE` under `.e2e/`, and an empty instance URL and API key.

   Tests exercise the real FastAPI + SQLite + sealed-credential stack. The only fake is
   `fake://` instance URLs, which the backend's connectivity check already simulates
   without network access. This follows the project's in-memory-fakes, no-mocks testing
   rule.
3. **Isolation:** one worker, serial execution (one backend, one SQLite file). An
   auto-fixture resets state through the public API before every test: it deletes all
   instances and disables the welcome modal.
4. **Layout:**
   - `web/playwright.config.ts` and `web/e2e/*.spec.ts`;
   - shared helpers in `web/e2e/fixtures.ts`;
   - `npm run test:e2e` runs the suite;
   - `tsconfig.json` includes `e2e/`, so the existing `web-typecheck` pre-commit gate
     covers the tests.
5. **Gate:** a `web-e2e` pre-commit hook at the `pre-push` stage, beside
   `pytest-pre-push`. It is registered in the `testing-standards` policy.
6. **Regression-first:** each UI defect gets a spec that fails on the defective code
   before it is fixed. The first spec, `admin-instances.spec.ts`, was confirmed to fail
   against the original admin panel.
7. **Artifacts:** traces and screenshots are kept on failure only, under
   `web/test-results/` and `web/playwright-report/` (both gitignored). Failure screenshots
   are also how the coding agent sees the rendered UI.

## Consequences

- UI regressions are caught before push, against the same stack users run.
- About 5 seconds per run (build plus server start). Pushes need Google Chrome installed.
- Selectors should prefer roles, visible text and `data-testid`. Locators pierce the
  components' open shadow roots, so no test-only hooks into Lit internals are needed.
- Follow-up audit: several other components have "offline fallback" branches
  (`now-workbench-shell`, `now-demo-catalog`, `now-otto-drawer`, `now-presenter-hud`,
  `now-fluent-explorer`, `now-welcome-modal`, `now-console`). Each needs an e2e spec
  proving it shows an explicit error or empty state instead of fabricated data.
