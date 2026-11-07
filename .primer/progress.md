# now-workbench -- Project Progress & Milestone Tracking

Last updated: 2026-11-06

## What Works

### Computed Numbers (2026-11-06)

- Tests: 775 collected (`pytest --collect-only`); 68 Playwright e2e tests in 17 specs; coverage 100%;
  new ADR-027/028 modules mutation-tested (mutmut, 967/967 killed; on demand, not a gate)
- Architecture: platform / domains / interfaces layers, 18 domain public roots, 20 import-linter
  contracts (ADR-015)
- Enforcement: 11 blocking pre-commit/pre-push gates + 7 baseline-tracked ratchets (governance.md)
- Ratchet baseline store: 2 entries in `.ratchet/baselines.json`
- Domains with `protocols.py`/`factory.py`: 0
- ADRs: 28 (`.primer/adr/`) | PRDs: 3 (`.primer/prd/`)

### Capability Inventory

EPIC-001 to EPIC-016 are done; their story list is in `archive/progress-history.md`.

### Since EPIC-016

- Live media capture against a real instance (`capture/`): authenticated Playwright recording,
  video proof deployment, natural-duration video honoring playbook wait pacing, purge controls,
  no silent mockup fallback in live mode; Otto `capture_media` tool receives instance credentials.
- Platform release compatibility (`releases/`): minimum-release validation, workspace evolution
  resolver, minimum release shown on catalog cards and modal.
- `workbench doctor` inspects stored database credentials.
- Versioned SQLite schema (v6) with AES-256-GCM sealed credentials and Claude key (ADR-012).
- Instance platform profile detected at connection (release, nodes, memory, build, database);
  the release is never typed, declared purpose kept apart from reported type (ADR-014).
- Deep-fix hardening: bundle-id path guard, loopback-only CORS/WS origins, honest failure
  reporting across pipeline, seed, properties, capture and plugins; UI never fabricates state.
- Otto-style UI (PRD-002): warm canvas, avatar messages, docked prompt, collapsible steps built
  from real tool runs, one-shot approval cards, detail side panel, live home tiles, left-menu
  Settings, ServiceNow-matched icons.
- Sign-in through Cloudflare Access (Apple, Google) with verified-token checks; admin and
  Solution Consultant roles stored in the database and managed on a Team screen; first admin
  by a one-time setup code from the server log; fail-closed when exposed without Access
  (ADR-016/017).
- Per-user profile: display name, 12 built-in avatars or an uploaded picture.
- Hardened container (non-root, no capabilities, `/healthz`), separate volumes for database
  and master key, `workbench backup`; deployed behind a dedicated Cloudflare tunnel on an
  isolated Docker network (ADR-017, `docs/deploy.md`). Claude key may come from `.env`.
- Everything per user via an ambient, fail-closed owner scope; groups (region, territory,
  business unit) with group admins; versioned artifacts shared with a group or everyone after
  approval; one resolver for bundle access (ADR-018, PRD-003).
- Impersonation ("View as someone"): admins act as anyone, group admins as their members,
  re-checked per request and logged (ADR-020).
- File attachments to Otto (PDF, images, text as Claude document/image blocks) and
  admin-set conversation limits (questions, age, file size and count) (ADR-021).
- Autonomous Otto: verifies its own actions (seed records by sys_id, live property values,
  plugin state from v_plugin, screenshots attached as images), up to 12 tool rounds,
  long replies kept alive past proxy timeouts; destructive tools still need Confirm.
- Real captures in the container (Chromium, login.do sign-in, fail-loud, no placeholders).
- Demo pipeline end to end on a live instance: modules, properties, Fluent app generated
  into the vendor scope and installed, seed, runbook test, video proof (ADR-022).
- Otto look and feel matched to EmployeeWorks; light only; resizable sidebar (ADR-019).
- Chart tiles (line, area, bar, pie, donut, meter, KPI sparklines) in plain SVG with smooth
  monotone curves and a data table view; `usage_history` and `seed_activity` chart the
  person's own activity (ADR-027).
- Telemetry: every action run and Claude call recorded per person (real actor under view-as),
  enforced by architecture tests; charts of tokens per day, action history, team usage
  (administrators) and live instance counts; Otto's text rendered as safe HTML (ADR-028).

## Known Issues

- Some components outside the deep-fix scope may still carry offline fallbacks (ADR-013 audit
  list).
- Otto's follow-up replies can misreport their own tool use (history carries text only).
- Chat feedback (thumbs, Get Help) is not built: it needs backend storage first.
- CLI bundle-id arguments are not path-guarded.
- Testers share the owner's Claude key; there is no per-user usage cap yet.
- Removing a deployed demo app from an instance is manual (System Applications).
- Capture scripts launch Chromium with `--ignore-certificate-errors`.
- Architecture policies `otto-copilot`, `demo-bundles`, `sqlite-persistence` are `unguarded`
  (no mechanical checks; agent-enforced via CLAUDE.md only).
