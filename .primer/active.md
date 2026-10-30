# now-workbench -- Active Work

Last updated: 2026-10-29
Branch: `main`
Python Version: `3.14.10`

## Current Focus

**Epic**: `EPIC-013` (Generative UI Tile Catalog, Tool-Based Multi-Tile Layouts & Adaptive Conversational Rendering).
**Active Milestone**: Implement structured Generative UI tile catalog, tool-based tile calling, and responsive multi-tile layout engine to eliminate raw markdown text dumps in conversational responses.

### Completed Foundation:
1. Python 3.14.10 environment configured with `uv` and `hatchling` backend (`EPIC-001`).
2. Demo bundle models, `BundleManager`, Table API transactional `SeedEngine`, and rollback tracking (`EPIC-002`).
3. Lit Web Components frontend scaffolded with ServiceNow Polaris/Lux theme, Next Experience shell, nav rail, demo catalog, and WebSocket `<now-console>` (`EPIC-003`).
4. Otto AI Copilot with `claude-sonnet-5-5` streaming, contextual workspace injection, deterministic simulation mode, and contextual intent chips (`EPIC-004`).
5. SQLite schema migrations and typed repository layer (`src/now_workbench/db/`) for multi-instance registry, templates, and threads (`EPIC-005`).
6. Workbench Typer CLI (`workbench doctor --fix`, `workbench demo seed/rollback/history`, `workbench instance list/add/activate/test`, `workbench template list/generate/inspect`).
7. 100% test coverage across all modules (2,621/2,621 statements), 91 passing tests, 0 Ruff lint violations, 0 Mypy strict errors.
8. Local enforcement ratchets (.ratchet/) passing 100% with zero mock policy and zero type-ignores.
9. "My ServiceNow" portal navigation and Welcome Modal aligned with official Next Experience design.
10. Antigravity Primer Workspace Skill installed (`.agents/skills/primer/`).
11. Reusable Parameterized Customization Template Engine (`EPIC-006`).
12. Conversational-First UI with Interactive Inline Widgets (`EPIC-007`).
13. Guided Demonstration Runbooks, Persona Presenter Mode HUD, and Table API verification (`EPIC-008`).
14. System Property Orchestration, Unified Teardown & Global Command Palette (`EPIC-009`).
15. Fluent SDK Schema Visualizer, AST Inspector & Studio Diff Engine (`EPIC-010`).
16. Now Workbench Settings, Live Configuration Persistence & Studio Preferences (`EPIC-011`).
17. DemoHub Parity, Dynamic Date Wizard, 1-Click Bundle Cloning, Safe Harbor & Strict Key Lifecycle (`EPIC-012`).

## Next Steps

1. Run `/primer sync` to finalize milestone bookkeeping.
2. Review product roadmap with user or brainstorm next capabilities.
