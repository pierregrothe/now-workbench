# ADR-019: Otto look and feel, matched to the owner's EmployeeWorks instance

**Status:** accepted
**Date:** 2026-11-06

## Context

The owner wants the workbench to look and behave "as close as possible" to ServiceNow's Otto, as
seen on their own EmployeeWorks instance (`my.servicenow.com/aiux/employeeworks/home`). The
owner's direction came in several requests on 2026-11-06. PRD-002 holds the product
requirements; this ADR records the presentation decisions so later work does not drift.

## Decision

- **Light only.** The dark theme, its preference, the Settings selector and the chat command
  that switched themes are removed (schema v7 strips the stored key). EmployeeWorks has no dark
  mode. Dark styles also made the new white cards unreadable.
- **Measure, then match.** Sizes and colors come from the live instance, read with the browser's
  computed styles, not from memory:
  - Canvas `#efece7`.
  - Prompt box 768px wide: a white inner box (radius 32px, 16px/24px text, padding about
    20/24px) inside an 8px warm ring `#f4f3f0`, with a soft drop shadow. The send button sits
    on its own row.
  - "Learn more" chip at the top right of Home: warm grey `#e4e1db`, radius 10px, 13px
    medium text, with a small tap glyph. Ours opens the welcome guide.
- **Our own drawings, never ServiceNow assets.** Icons are drawn in `web/src/icons.ts` to match
  the observed style (thin outlines, rounded caps). ServiceNow's SVG sprite files are not copied.
  The icons are:
  - the paper-plane send button;
  - Otto's diamond glyph;
  - the open arrow;
  - the library icon;
  - the menu-style sidebar toggle (three lines and a chevron);
  - the tap glyph.
- **Navigation like EmployeeWorks.**
  - A "Recent" header with a compose button (aria-label "New conversation") replaces the
    dashed "New Conversation" button and the "Active/Past" labels.
  - The top bar blends into the canvas.
  - Settings uses a left menu of sections.
- **Accessible names stay stable** ("Send", "New conversation", "Learn more", "Collapse
  sidebar"), so Playwright specs (ADR-013) assert behaviour and a few key computed colors rather
  than markup.

## Consequences

- Visual changes are checked against the live instance before they ship. When EmployeeWorks
  changes, this ADR is amended, not silently overridden.
- The screens listed follow these measurements: chat, Settings, Synthesizer, Media Capture,
  Fluent Explorer and the Artifact library; PRD-002 records the restyles. The Synthesizer and
  Media Capture were restyled on 2026-11-07 (story 2026.11b.02): pill buttons, 10px fields,
  warm segmented chips, 16px cards. The Fluent Explorer and the Artifact library cards followed
  the same day (story 2026.11b.03): the Otto canvas, a Settings-style tables menu, round icon
  buttons, warm chips and the shared form styles.
- Still to restyle: the buttons of the Settings Instances section (`admin-shared-styles`), the
  admin panel canvas, and the share, clone and deploy dialogs (inline styles, 6px inputs).
