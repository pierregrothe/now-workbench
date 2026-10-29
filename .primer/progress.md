# now-workbench -- Progress & Milestones

## Milestones

- [x] **M1: Project Initialization & Primer Setup** (2026-10-29)
  - Scaffolding of `.primer/` context (`charter.md`, `stack.md`, `product.md`, `brief.md`, `patterns.md`, `decisions.md`, `board.json`).
  - Git repository initialized.
- [x] **M2: Core Package & Toolchain Tooling** (2026-10-29)
  - Python 3.14.10 runtime pinned with `uv`.
  - Pydantic v2 data models for bundles, manifests, and runner results.
  - Initial `NowSdkRunner` with in-memory fake testing.
- [x] **M3: ServiceNow Lux UI & Otto Copilot** (2026-10-29)
  - Open-standard Lit Web Components UI styled to match ServiceNow Lux.
  - Embedded Otto copilot with Anthropic Claude streaming integration.
  - Live console streaming interface for `now-sdk` outputs.
- [ ] **M4: Seed Data Engine & Instance Provisioning** (Planned)
  - Transactional seed loader communicating with ServiceNow Table API.
  - Automatic rollback and teardown of seeded demonstration records.
- [ ] **M5: Interactive Otto Tool-Calling** (Planned)
  - Otto capability to generate Fluent TypeScript definitions on demand.
  - Conversational demo deployment and instance diagnostics.
