# Brainstorming: Conversational Workbench, Instance Registry, and Themed Templates

Date: 2026-10-29
Mode: First Principles, Domain-Driven Design, Failure Analysis
Status: Approved

## Context Brief

`now-workbench` is evolving from a static demo catalog viewer into an AI-native
conversational workbench for the ServiceNow Fluent SDK (@servicenow/sdk).
The developer and solution consultant experience requires:
1. A simplified, enterprise-grade "My ServiceNow" portal interface that strips
   out low-level plumbing details (such as raw Claude API model badges).
2. A dedicated Admin & Diagnostics panel encapsulating system telemetry and
   the `workbench doctor` health checks.
3. A multi-instance registry backed by SQLite to register, select, and target
   different ServiceNow environments (PDIs, customer sub-prods, sandboxes).
4. A conversational-first interaction paradigm featuring rich, interactive inline
   widgets in the chat stream (instance selectors, schema diffs, execution cards).
5. A reusable customization template engine with customer-specific branding
   placeholders (names, logos, color schemes, assignment groups).

## Key Insights & Irreducible Responsibilities

1. **Interface Simplicity & Enterprise Trust**:
   Customer-facing Solution Consultants and platform developers need an interface
   that looks and feels like authentic ServiceNow software. Disclosing raw API keys,
   model strings (e.g. `claude-sonnet-5-5`), or token counts in the top chrome creates
   visual noise and distracts from customer demonstrations. All diagnostics belong in
   a dedicated Admin Panel.

2. **Persistence Layer (SQLite via stdlib sqlite3 / aiosqlite)**:
   In-memory state does not survive server restarts. Storing instances, customer
   customization configurations, and conversational thread history requires an
   embedded, zero-configuration relational store. SQLite in WAL mode provides
   instantaneous queries, transactional safety, and zero external daemon overhead.

3. **Multi-Instance Registry as Execution Target**:
   Customization tasks (building Fluent TypeScript, deploying scoped applications,
   injecting Table API seed data, and rolling back demo records) must never be hardcoded
   to a single instance URL in `.env`. The instance registry enables users to register
   multiple instances (e.g. "Acme Corp PDI", "Demo Sandbox", "Zurich Testbed") and
   route any task to the selected target.

4. **Conversational UI with Actionable In-Chat Widgets**:
   Text-only responses force users to jump out of chat to take action. In an
   AI-native workbench, Otto generates structured interactive widgets directly in
   the conversation flow:
   - `InstanceSelectorWidget`: Pick the deployment target from the registry.
   - `CustomerThemeFormWidget`: Enter customer name, brand colors, and logo.
   - `FluentSchemaDiffWidget`: Review generated *.now.ts code before deployment.
   - `ExecutionProgressWidget`: Stream live now-sdk compiler and Table API logs.
   - `RollbackWidget`: 1-click cleanup of injected demo records.

5. **Parameterized Customization Templates**:
   Demonstrations should be reusable across multiple prospects with zero manual code
   rewrites. Templates use standard mustache/jinja placeholders:
   - Brand: `{{customer_name}}`, `{{customer_logo}}`, `{{primary_color}}`, `{{accent_color}}`
   - Platform: `{{scope_prefix}}`, `{{assignment_group}}`, `{{incident_category}}`
   When instantiated, the template compiles into a customized bundle ready for
   immediate deployment.

## Architectural Decisions

- **ADR-006: Local SQLite Persistence Engine**:
  Embed SQLite (`data/workbench.db`) using pure Python standard library `sqlite3`
  with async connection pooling, WAL journaling, and strict schema versioning.
- **ADR-007: Parameterized Customization Template Engine**:
  Define declarative templates with `template.json` manifests, templated Fluent
  sources (`fluent/app.now.ts.tpl`), and parameterized seed datasets.

## Feature Breakdown by Epic

### EPIC-005: SQLite Persistence & Multi-Instance Registry
- **STORY-011**: Implement SQLite database connection layer, schema migrations,
  and repository abstractions for instances, templates, and chat threads.
- **STORY-012**: Build Multi-Instance Registry backend API (`/api/instances`)
  and CLI commands (`workbench instance list/add/switch/test`).
- **STORY-013**: Route all SDK build, deploy, and seed operations to the
  selected registry instance profile.

### EPIC-006: Reusable Parameterized Customization Templates
- **STORY-014**: Author template substitution engine for brand placeholders
  (`customer_name`, `logo`, `colors`, `scope`).
- **STORY-015**: Parameterize starter bundle (`sample-ai-assistant`) into a
  reusable enterprise template.
- **STORY-016**: Build Template Management API and CLI (`workbench template list/generate`).

### EPIC-007: Conversational-First UI with Interactive Inline Widgets
- **STORY-017**: Simplify UI chrome and navigation; remove raw model and API plumbing.
- **STORY-018**: Implement dedicated Admin & Diagnostics Modal (`workbench doctor` GUI).
- **STORY-019**: Build Lit Web Component interactive inline widgets (instance selector,
  theme configurator, build progress card, seed rollback ledger).
- **STORY-020**: Refactor primary viewport into persistent conversational threads
  backed by SQLite.
