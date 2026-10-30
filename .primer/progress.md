# now-workbench -- Project Progress & Milestone Tracking

Last updated: 2026-10-29

## Completed Epics & Stories

- **EPIC-001: Foundation & Runtime Toolchain** [DONE]
  - STORY-001: Scaffolding, Python 3.14.10, uv, Pydantic v2, Typer CLI.
  - STORY-002: NowSdkRunner subprocess executor with in-memory deterministic fakes.
  - STORY-003: Multi-stage Dockerfile and docker-compose.
- **EPIC-002: Demo Bundle Packaging & Seed Engine** [DONE]
  - STORY-004: DemoBundle packager, unpacker, manifest validator.
  - STORY-005: Table API transactional seed record loader & rollback tracker.
- **EPIC-003: ServiceNow Lux / Polaris Web UI** [DONE]
  - STORY-006: Lit + Vite + TypeScript frontend with Polaris CSS tokens.
  - STORY-007: Shell, Nav Rail matching "My ServiceNow", Demo Catalog, Welcome Modal.
  - STORY-008: Live console terminal output streaming component.
- **EPIC-004: Otto AI Copilot with Claude API** [DONE]
  - STORY-009: Claude streaming client upgraded to `claude-sonnet-5-5`.
  - STORY-010: Conversational drawer with contextual intent chips.
- **EPIC-005: SQLite Persistence & Multi-Instance Registry** [DONE]
  - STORY-011: SQLite schema migrations and repository layer.
  - STORY-012: Multi-Instance Registry API and CLI commands.
  - STORY-013: Target instance binding for customization operations.
- **EPIC-006: Reusable Parameterized Customization Templates** [DONE]
  - STORY-014: Template placeholder substitution engine (`{{customer_name}}`, `{{logo}}`, `{{colors}}`).
  - STORY-015: Parameterized enterprise reference template.
  - STORY-016: Template management API and CLI.
- **EPIC-007: Conversational-First UI with Interactive Inline Widgets** [DONE]
  - STORY-017: UI de-cluttering (remove raw model/API indicators).
  - STORY-018: Dedicated Admin & Diagnostics Modal (`workbench doctor` GUI).
  - STORY-019: Interactive in-chat widgets (InstanceSelector, ThemeForm, BuildRunner, Rollback).
  - STORY-020: Persistent conversational workspace backed by SQLite.
- **EPIC-008: Guided Demonstration Runbooks & Persona Presenter Mode** [DONE]
  - STORY-021: Walkthrough Runbook parsing, Pydantic models, and stage extraction engine.
  - STORY-022: Runbook API endpoints (`GET /api/demos/{id}/runbook`, `POST /verify-stage`).
  - STORY-023: `<now-presenter-hud>` Lit component with persona switcher and talking points.
  - STORY-024: CLI runbook commands (`workbench demo runbook`, `workbench demo verify-stage`).
- **EPIC-009: System Property Orchestration, Unified Teardown & Global Command Palette** [DONE]
  - STORY-025: System Property transactional snapshot, apply, and restore engine (`PropertyEngine`).
  - STORY-026: Property & Demo Teardown REST API (`/api/demos/{id}/properties`, `/reset`) & CLI commands (`workbench demo properties`, `workbench demo reset`).
  - STORY-027: `<now-command-palette>` Lit component with `Cmd+K` keyboard shortcut and deep action routing.
  - STORY-028: Unified 1-click demo reset flow (seed rollback + property restoration + audit log).
- **EPIC-010: Fluent SDK Schema Visualizer, AST Inspector & Studio Diff Engine** [DONE]
  - STORY-029: Fluent AST parser, Pydantic models, and schema diff engine (`src/now_workbench/fluent/`).
  - STORY-030: Fluent Schema REST API (`/api/demos/{id}/fluent`, `/diff`) & CLI commands (`workbench demo fluent inspect`, `workbench demo fluent diff`).
  - STORY-031: `<now-fluent-explorer>` Lit component in Studio nav tab.
  - STORY-032: Otto Copilot contextual Fluent schema analysis, explanation, and synthesis assistance.
