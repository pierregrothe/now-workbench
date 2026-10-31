# ADR-010: Lit 3 Reactive Controllers, Lit Context, and Modular Web Component Hierarchy

**Status:** accepted
**Date:** 2026-10-30

## Context

The frontend was originally implemented with Lit Web Components to match ServiceNow's Lux design system
(ADR-001). However, as features grew, `now-conversational-workspace.ts` ballooned into a 4,738-line monolith
mixing CSS styles, application routing, thread CRUD, capture polling, synthesizer forms, and 9 different tile
renderers. This violated maintainability principles, slowed code navigation, and created deep prop-drilling
between the root shell and leaf components.

## Decision

1. **Lit Context (`@lit/context`) for Global State**:
   - Provide workbench-wide state (`activeTab`, `selectedBundleId`, `selectedInstanceId`, `themeMode`)
     at the root `<now-workbench-shell>` using `@provide({ context: workbenchContext })`. Leaf components
     consume state via `@consume({ context: workbenchContext, subscribe: true })`, eliminating prop-drilling.
2. **Reactive Controllers for Async Workflows**:
   - Encapsulate data fetching, polling, and WebSocket streaming into reusable Lit `ReactiveController`
     classes (`ThreadListController`, `CaptureGalleryController`, `DemoPipelineController`) rather than
     embedding lifecycle logic inside UI component classes.
3. **Strict Component Directory Hierarchy (Capped at 500 Lines)**:
   - Decompose monolithic views into dedicated subdirectories:
     - `web/src/views/`: Primary route views (`now-chat-view.ts`, `now-synthesizer-view.ts`, `now-capture-studio.ts`).
     - `web/src/tiles/`: Individual Generative UI tile renderers (`now-media-tile.ts`, `now-table-tile.ts`).
     - `web/src/modals/`: Standalone lightbox and onboarding dialogs.
     - `web/src/styles/`: Shared Lux CSS blocks.
4. **Enforcement Ratchet for TypeScript File Sizes**:
   - Extend the file-size pre-commit gate and `.ratchet/count_file_size.py` to enforce a 500-line limit
     on all source files under `web/src/`.

## Consequences

- Monolithic files are eliminated; no single component file exceeds 500 lines.
- Asynchronous data fetching is decoupled from UI rendering and easily testable.
- Shadow DOM encapsulation prevents style leakage while shared CSS tokens preserve ServiceNow Lux fidelity.
