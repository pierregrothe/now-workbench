# Decision Log (ADRs)

Append-only record of architectural and design decisions for `now-workbench`.

---

### 2026-10-29 -- ADR-001: Hybrid Runtime with Python Core & Lit Web Components

**Status:** accepted
**Context:**
`@servicenow/sdk` runs on Node.js, but Python 3.14 + Pydantic v2 gives agents higher velocity
and cleaner schema validation; the UI must replicate ServiceNow's Lux design language.
Full rationale: `.primer/adr/ADR-001-hybrid-runtime-python-lit.md`.
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

---

### 2026-10-29 -- ADR-005: Constitutional Governance and 3-Tier Enforcement Model

**Status:** accepted
**Context:**
Humans and AI agents co-develop `now-workbench`; a graduated (not "block or ignore")
governance model prevents regressions and drift. Full text: ADR-005 in `.primer/adr/`.
**Decision:**
1. Adopt Primer's 3-Tier Enforcement Model:
   - Tier 1: Deterministic blocking pre-commit gates (Ruff, Mypy, Pytest fakes, file-size, primer-reconcile).
   - Tier 2: Non-decreasing metric ratchets in `.ratchet/` (coverage, complexity, file sizes, type-ignores, relative imports).
   - Tier 3: Soft / advisory notices.
2. Establish non-negotiable constitutional invariants: Python 3.14.10, uv package manager,
   no mocks in tests (in-memory fakes only), Pydantic v2 strict models, async subprocess streaming,
   absolute imports, Lit Web Components with ServiceNow Lux CSS tokens, and ASCII-only characters.
3. Exclude unrelated domain rules (e.g. financial market rules) to keep governance lean and focused.

**Consequences:**
- Commits are validated against strict contracts; quality baselines can only improve.

---

### 2026-10-29 -- ADR-006: Local SQLite WAL Persistence and Scoped Repository Pattern

**Status:** accepted

**Context:**
`now-workbench` manages stateful local resources across CLI and API processes: instances, templates,
threads, and seed audit logs. Ad-hoc connections risked lock contention and unclosed warnings.

**Decision:**
1. Use embedded SQLite in WAL mode (`PRAGMA journal_mode=WAL;`) with foreign keys enabled.
2. Use scoped `db_session()` context manager for all DB operations.
3. Encapsulate queries inside `DatabaseRepository` returning frozen Pydantic v2 records.

**Consequences:**
- Safe concurrent read access between CLI and API processes.
- Zero unclosed resource warnings and deterministic in-memory testing.

---

### 2026-10-29 -- ADR-007: Transactional Seed Engine, Snapshot Property Orchestration, and Unified Teardown

**Status:** accepted

**Context:**
Demonstrations mutate live instance state (Table API seed records and sys_properties). Repeated runs
leave orphaned records and configuration drift.

**Decision:**
1. Track every created record in `seed_operations` and support reverse-order rollback.
2. Snapshot existing system properties before overrides and restore them on demand.
3. Provide unified `workbench demo reset` combining seed deletion and property restoration.

**Consequences:**
- Zero pollution on target developer instances after demo completions.

---

### 2026-10-29 -- ADR-008: Balanced-Brace Fluent SDK Schema Parser and Diff Engine

**Status:** accepted

**Context:**
Visualizing and diffing Fluent `*.now.ts` schema definitions required spawning slow Node.js compiler processes.

**Decision:**
Implement a deterministic zero-subprocess balanced-brace scanner in Python to extract table definitions,
columns, and calculate structural diffs in sub-milliseconds.

**Consequences:**
- Instant schema exploration and diffing without Node runtime overhead.

---

### 2026-10-30 -- ADR-009: Declarative Demo Playbooks, Native Shadow-DOM Automation, and Storage State Session Persistence

**Status:** accepted

**Context:**
Demonstrations require verifiable proof of user interaction (connecting, cursor movement, clicking, typing)
on ServiceNow Next Experience (Polaris), which heavily utilizes nested Shadow DOM structures.

**Decision:**
1. Define executable `walkthrough/playbook.json` playbooks per bundle.
2. Utilize native Shadow-DOM piercing locators for web components and form iframes.
3. Persist authenticated session cookies (`storage_state`) to eliminate repetitive logins.
4. Record multi-step execution into native VP8 WebM video proofs with step execution logs.

**Consequences:**
- Verifiable, non-simulated demo execution videos showing realistic cursor paths and actions.

---

### 2026-10-30 -- ADR-010: Lit 3 Reactive Controllers, Lit Context, and Modular Web Component Hierarchy

**Status:** accepted

**Context:**
The frontend grew into a 4,738-line monolith (`now-conversational-workspace.ts`) mixing CSS, routing,
thread fetching, media capture, and tile rendering.

**Decision:**
1. Adopt `@lit/context` for root workbench state injection, eliminating prop-drilling.
2. Encapsulate async logic into Lit `ReactiveController` classes.
3. Decompose monolithic components into modular views, tile renderers, and modals under `web/src/`.
4. Enforce a strict 500-line cap on TypeScript frontend files via metric ratchets.

**Consequences:**
- High maintainability, sub-500 LOC files, clean Shadow DOM style encapsulation, and modular testing.

---

### 2026-10-30 -- ADR-011: Unified Async Claude Agent Loop with Streaming Tool Events and Diagnostic Transparency

**Status:** accepted

**Context:**
Dual AI execution pathways (synchronous REST messages vs text-only WebSocket) caused fragmented state,
and unhandled errors silently fell back to fake static templates in live mode.

**Decision:**
1. Consolidate into a unified `AsyncAnthropic` streaming agent engine with prompt caching.
2. Stream tool execution lifecycle events (`TOOL_CALL_START`, `TOOL_CALL_RESULT`, `TILE_RENDER`) to the UI.
3. Eliminate silent fake fallbacks in live mode (`fake_mode=False`), surfacing actionable diagnostic tiles on error.

**Consequences:**
- Sub-second streaming perceived latency, unified message history, and transparent error reporting.

---

### 2026-11-06 -- ADR-012: Versioned SQLite Schema and AES-256-GCM Credential Sealing

**Status:** accepted (amends ADR-006)

**Context:**
Prototype persistence leaked decrypted instance passwords through `/api/instances`, rewrote
passwords as plaintext on update, kept its master key beside the DB, and re-ran DDL on every session.

**Decision:**
1. Seal instance credentials (username + password) and the Claude API key with AES-256-GCM
   (`cryptography`), context-bound via associated data; master key outside `data/`
   (`WORKBENCH_MASTER_KEY` > `WORKBENCH_KEY_FILE` > `~/.config/now-workbench/master.key`).
2. API returns `InstancePublic` (no password). 3. `PRAGMA user_version` migrations; STRICT
   tables with UNIQUE/CHECK/FK-cascade constraints; WAL + busy_timeout + synchronous=NORMAL.

**Consequences:**
- A copied `workbench.db` yields no secrets; losing the master key loses stored credentials.

---

### 2026-11-06 -- ADR-013: Playwright End-to-End UI Testing Against the Real Backend

**Status:** accepted

**Context:**
The admin panel rendered a hardcoded "authenticated" sample instance over an empty DB; no test
could see it because the defect lived only in the rendered UI.

**Decision:**
1. `@playwright/test` on local Google Chrome; `webServer` builds the UI and runs the real
   backend with isolated `.e2e/` data + key (no API mocks).
2. Serial, API-reset fixtures; `web-e2e` pre-push gate; regression-first specs.

**Consequences:**
- UI regressions block push; pushes need Google Chrome. Offline-fallback branches in other
  components are queued for e2e audit.

---

### 2026-11-06 -- Instance release family is detected, never user-selected

**Status:** accepted
**Context:**
The connect form asked for the release family and defaulted to Zurich; a live instance running
Australia was stored as Zurich, and Australia was missing from `RELEASE_FAMILIES` (unknown names
compared lexically, so it ranked as the *oldest* release).
**Decision:**
1. `check_and_record_instance()` is the single "test this instance" path (all 12 former
   verify+update call sites): on authentication it reads `glide.war` from `sys_properties`
   (`releases/detection.py`) and stores the family; simulated (`fake://`) instances are never probed.
2. Undetectable (e.g. no read on `sys_properties`) leaves the stored value; new instances start as
   `Unknown`, never a guessed family. Add/edit forms show no picker (edit shows it read-only).
3. `RELEASE_FAMILIES` gains Australia; compact build tokens (`washingtondc`, `sandiego`) normalize.

**Consequences:**
- Release-gated features (ADR-009 workspaces, minimum-release checks) use the instance's real build.

---

### 2026-11-06 -- ADR-014: Instance Platform Profile Detected at Connection

**Status:** accepted (supersedes the "release family is detected" entry above)

**Context:**
Release names cannot be planned like version numbers; a stored, settable release column plus a
hardcoded name list kept drifting. The owner wants all key facts (prod/dev, datacenter, CPU, memory).

**Decision:**
1. Schema v2 drops `instances.release`; release is derived from `instance_profiles` and never input.
2. Every successful check reads `sys_properties`, `sys_cluster_state`, `sys_cluster_node_stats`
   into `instance_profiles` + `instance_nodes` (best-effort; never invented for `fake://`).
3. Unlisted release names rank newest; `Unknown` never satisfies a requirement.

**Consequences:**
- New ServiceNow releases need no code change; memory figures are JVM heap per node.

---

### 2026-11-06 -- ADR-014 amendment: reported platform type vs. declared purpose

**Status:** accepted

**Context:**
A standalone demo instance reports `instance_type=prod` and `glide.installation.production=true`; the
UI showed a red PROD badge for it, which was misleading.

**Decision:**
1. New `instances.purpose` (demo/development/test/production, default demo), declared by the owner.
2. Reported values renamed `instance_type` / `production_property` and labelled "(reported)".

**Consequences:**
- Warning styling and future production guards key off the owner's declaration, never the platform's.


### 2026-11-06 -- ADR-016: Cloudflare Access sign-in and roles

Sign-in through Cloudflare Access (Apple, Google); the server verifies the signed token and maps
the verified email to `admin` and `solution_consultant` from configuration. Fails closed when
exposed without Access. The earlier email-code approval design was dropped before release.
Details: `.primer/adr/ADR-016-cloudflare-access-sign-in-and-roles.md`.

### 2026-11-06 -- ADR-017: Container deployment and first-run setup

One hardened container on srv01chambly behind Cloudflare Access. The first administrator is
created with a one-time setup code written only to the server log (more secure than a
first-come password form); roles then live in the database and are managed on a Team screen.
Secrets are entered in the UI only and sealed; the master key and the database are in separate
volumes. Runbook: `docs/deploy.md`. Details: `.primer/adr/ADR-017-container-deployment-and-first-run-setup.md`.

### 2026-11-06 -- ADR-017 amendment: Claude key from the server .env

At the owner's request the shared Claude key may be set as `WORKBENCH_ANTHROPIC_API_KEY` in the
server's `.env` (mode 600, never committed). When set, it wins over a key entered in Settings,
is never written to the database, and shows read-only in the UI. Home users reach the
workbench through Cloudflare via split-horizon A/AAAA overrides on the NAS DNS (runbook).
Details: `.primer/adr/ADR-017-container-deployment-and-first-run-setup.md`.

### 2026-11-06 -- ADR-018: Owner-scoped repository, groups and versioned sharing

Everything (instances with credentials, conversations, seed runs, preferences, demo bundles)
belongs to one person. The verified email is an ambient owner set by the access middleware;
owner-scoped queries fail closed without it. Groups (region, territory, business unit) have
group admins who accept members and approve group shares; global shares need an administrator.
Each version is an immutable snapshot and needs its own approval. Product decisions: PRD-003.
Details: `.primer/adr/ADR-018-owner-scoped-repository-groups-and-versioned-sharing.md`.

### 2026-11-06 -- ADR-019: Otto look and feel matched to EmployeeWorks

Light only (dark theme removed). Sizes and colors are measured on the owner's EmployeeWorks
instance (768px two-layer prompt box, warm canvas, Learn more chip). Icons are our own
drawings in that style, never copied ServiceNow assets. Navigation follows EmployeeWorks
(Recent header with compose, left-menu Settings).
Details: `.primer/adr/ADR-019-otto-look-and-feel-alignment.md`.

### 2026-11-06 -- ADR-020: Impersonation ("View as someone")

Administrators may act as anyone; group administrators as members of their groups, never as a
workbench administrator. The impersonation is held server-side per signed-in person and applied
by the access middleware, so every workload runs as the target. Rights are re-checked on each
request (revoked when lost); starts, stops and revocations are logged; a banner offers Stop.
Details: `.primer/adr/ADR-020-impersonation.md`.

### 2026-11-06 -- ADR-021: File attachments and conversation limits

People attach PDFs, images and text files to a question; Claude receives them as document and
image blocks. Administrators set one global limit set: question and age caps per conversation,
per-file size, and per-conversation file count and total (defaults 20 questions, 30 days,
10 MB, 10 files, 25 MB). Types are detected from the bytes; enforcement is server-side on every
path. Details: `.primer/adr/ADR-021-attachments-and-conversation-limits.md`.

### 2026-11-06 -- ADR-022: Deploying a demo's Fluent app

The pipeline generates one SDK project per bundle and vendor: scope x_<vendor>_<6 hex>,
vendor read from the instance, tables renamed into the scope (seeds and runbook stages
follow), shared SDK toolchain, build then install with the SDK's non-interactive CI
credentials. Bundles that already are SDK projects deploy as is; bundles without Fluent
sources skip deploy. Details: `.primer/adr/ADR-022-fluent-app-deploy-from-demo-bundles.md`.

### 2026-11-06 -- ADR-023: Prompt caching, compaction and token budgets

Otto replays each conversation byte for byte from stored transcripts (no sliding window), with
a 1-hour cached tools+system prefix and automatic caching along the conversation. Server-side
compaction summarizes long conversations at an admin-set size. The question cap became a
per-conversation token budget counted as billed. Usage is logged per reply.
Details: `.primer/adr/ADR-023-prompt-caching-compaction-and-token-budgets.md`.

### 2026-11-07 -- ADR-015 accepted: layered packages, per-domain repositories

Code moves to `platform/` (no domain knowledge), `domains/<name>/` (public root per domain)
and `interfaces/` (api, cli, ai), enforced by import-linter. Each domain owns its repository
over a shared connection; the `DatabaseRepository` facade goes. The pipeline becomes
`domains/demos`; `ai/actions.py` is deleted; web components wait for their own ADR.
Details: `.primer/adr/ADR-015-domain-oriented-package-architecture.md`.

### 2026-11-07 -- ADR-024: Web component structure

Component CSS moves to sibling `*-styles.ts` files with shared partials; store access goes
through one `StoreController`; the views' copied top bar becomes `<now-workspace-bar>`;
components still over 500 lines split into one child element per section. The web size
baseline must end empty. The unmounted `now-otto-drawer` is deleted.
Details: `.primer/adr/ADR-024-web-component-structure.md`.

### 2026-11-07 -- ADR-025: Otto's tool set and visual tile catalog

Rules move from API routes into domain services shared by the API and Otto's tools; tools run
as the signed-in person. New tools cover groups, sharing, approvals, versions, team and
limits (impersonation stays UI-only, owner's choice). A `show` tool lets Otto present
entity tiles loaded by id on the server and generic tiles it composes; tiles reuse the app's
elements. Details: `.primer/adr/ADR-025-otto-tool-set-and-visual-tiles.md`.

### 2026-11-07 -- ADR-026: Conversational control and UI parity

Otto gets a per-person system block (roles, groups, view-as) and role-filtered tools; it can
move the interface with `open_screen`, and the interface refreshes after Otto acts. The tool
registry becomes the interface's action catalog: an Actions screen runs any capability by
hand under the same rules. Details: `.primer/adr/ADR-026-conversational-control-and-ui-parity.md`.

### 2026-11-07 -- ADR-027: Chart tiles and history tools

`show` gains a `chart` kind (line, area, bar, pie, donut, meter) and KPI sparklines, drawn in
plain SVG with no chart library, on the validated categorical palette, with a data table view.
`usage_history` and `seed_activity` chart the person's own stored activity. The tool registry
now refuses duplicate names. Details: `.primer/adr/ADR-027-chart-tiles-and-history-tools.md`.

### 2026-11-07 -- ADR-028: Telemetry, live instance charts and rendered text

Every action run (`execute_tool`) and every Claude call (`_AgentLoop.absorb`, recorded stream)
is stored per person with the real actor; architecture tests fail the build on any bypass.
New charts: tokens per day, action history, team usage (administrators), live instance counts
from the Aggregate API. Otto's markdown renders through a safe Lit renderer, never raw HTML.
Charts stay plain SVG (owner's choice). Details: `.primer/adr/ADR-028-telemetry-and-live-instance-charts.md`.

### 2026-11-07 -- ADR-029: Mutation gate, telemetry retention and S3 backups

A pre-push `mutation-gate` fails the push unless mutmut kills every mutant of the gated modules
(ADR-027/028/029 code); timeouts are re-run once alone (a mutmut fork-server deadlock), and
survivors are never retried. Telemetry is purged past `WORKBENCH_TELEMETRY_RETENTION_DAYS`
(default 365, minimum 60, the longest chart), at startup and daily. `workbench backup --s3`
uploads the snapshot to an S3-compatible bucket, signed with SigV4 over httpx (no AWS SDK).
Details: `.primer/adr/ADR-029-mutation-gate-telemetry-retention-s3-backups.md`.

### 2026-11-07 -- ADR-030: Phone and tablet layouts

At `(max-width: 768px), (max-height: 500px)` the navigation rail becomes a drawer opened from a
phone top bar; two-pane screens (Settings, Fluent, Synthesizer, Capture, Actions) stack at 900px
or less. `100dvh`, safe areas, 16px fields (no iOS zoom), 40px touch targets, and no tooltips on
touch. Plain CSS media queries, no dependency; 16 Playwright tests cover phone, landscape,
tablet and desktop. Details: `.primer/adr/ADR-030-phone-and-tablet-layouts.md`.
