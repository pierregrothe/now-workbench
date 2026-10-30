# Brainstorm: Now Workbench Settings & Live Preferences (EPIC-011)

## 1. Problem Statement

Previously, the bottom settings item in the left navigation rail opened an Instance Registry panel (`<now-admin-panel>`). However, the settings menu of **Now Workbench** should configure **Now Workbench itself** -- its Playwright capture defaults, Solution Consultant synthesis defaults, AI intent routing behavior, local Fluent SDK toolchain mode, and UI/Presenter HUD preferences -- while keeping ServiceNow Instance connections separate.

## 2. Design Decisions (Aligned with User)

1. **Pure Now Workbench Configuration**:
   - The **Settings** menu (`Workbench Settings` in the left navigation rail) is dedicated to Now Workbench preferences across 5 structured categories:
     1. **Playwright Capture Defaults**: Default browser viewport (`1440x900`, `1920x1080`, `1280x720`), default capture format (`screenshot` vs `video`), page settle timeout (`ms`), and offline deterministic fallback (`fake_mode`).
     2. **SC & Demo Synthesis Defaults**: Default Solution Consultant author name/email, default ServiceNow release (`Zurich`, `Yokohama`, `Xanadu`), default scoped table prefix (`x_snc_`), default brand accent color (`#62d84e`), and narrative tone (`executive`, `technical`, `rapid`).
     3. **AI Copilot & Intent Router**: Claude model selection (`claude-sonnet-5-5`, etc.), auto-route left menu on intent detection (`auto_route_intent`), and auto-execute on route (`auto_execute_intent`).
     4. **Fluent SDK & Local Toolchain**: SDK execution mode (`sdk_fake_mode`), `now-sdk` / `node` binary paths, and embedded `workbench doctor` health status.
     5. **UI & Presenter HUD**: Show `Welcome to Now Workbench` modal on startup (`show_welcome_on_startup`), default sidebar state (`sidebar_collapsed`), and Presenter HUD teleprompter font scale (`hud_font_scale`).
2. **Full-Stack SQLite Persistence + REST API + CLI**:
   - Stored in SQLite (`workbench_settings` table in `src/now_workbench/db/`) via `Repository.get_workbench_settings()` and `Repository.update_workbench_settings()`.
   - Exposed via `GET /api/settings`, `PUT /api/settings`, and `POST /api/settings/reset`.
   - Exposed via CLI: `uv run workbench config show`, `uv run workbench config set`, and `uv run workbench config reset`.
   - Consumed automatically by `PlaywrightCaptureEngine` and `UseCaseSynthesizer` when request fields use workbench defaults.
3. **Separate Instance Connections**:
   - ServiceNow Instance connections remain accessible as a dedicated sub-view inside Artifact/Seeding workflows and via a secondary tab, keeping `Workbench Settings` focused on Now Workbench configuration.

## 3. Epic & Story Decomposition (EPIC-011)

- **STORY-033**: Implement SQLite persistence & strict Pydantic v2 models (`WorkbenchPreferences`, `WorkbenchPreferencesUpdate`) for Now Workbench Settings.
- **STORY-034**: Implement REST API (`/api/settings`) and CLI (`workbench config show/set/reset`) for live workbench preferences.
- **STORY-035**: Wire `PlaywrightCaptureEngine` and `UseCaseSynthesizer` to consume persisted Workbench Settings defaults.
- **STORY-036**: Build `<now-workbench-settings>` Lit component and wire live preferences into `<now-workbench-shell>`.
