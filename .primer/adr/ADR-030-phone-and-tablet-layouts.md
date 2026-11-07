# ADR-030: Phone and Tablet Layouts

**Status:** accepted 2026-11-07
**Date:** 2026-11-07
**Builds on:** ADR-019 (Otto look), ADR-024 (component structure)

## Context

The owner noticed (2026-11-07) that the UI did not adapt to phones. Measured at 390 x 844
(iPhone): the 248px navigation rail left about 140px for every screen. The Settings section
menu, the Fluent explorer and the Synthesizer and Capture forms were squeezed or overflowed.
The welcome guide's 320px step list left no room for its text. Tooltips stayed on screen after
a tap. At 820 x 1180 (iPad portrait), Settings kept its side menu next to a cramped card.

## Decision

Targets: phones in portrait (iPhone 390, Android 412) and landscape (844 x 390), tablets in
portrait (iPad 820), and desktop unchanged.

- **Phone layout** applies at `(max-width: 768px), (max-height: 500px)`, so landscape phones
  count too. The rail becomes an off-canvas drawer (`<now-nav-rail drawer>`). A top bar
  (`<now-mobile-bar>`) names the screen and opens the drawer. The drawer closes on
  navigation, on Escape, and on a tap on the scrim. While it is open the content is `inert`.
  The state lives in `MobileNavController`.
- **Two-pane screens stack at 900px or less** (tablet portrait included): Settings sections and
  Fluent tables become a horizontal strip above the content. The Synthesizer and Capture forms
  sit above their results. On the Actions screen the chosen action's form comes first.
- **Phone details:** `100dvh` and safe-area insets (`viewport-fit=cover`) for notches and the
  home indicator. Gutters drop from 36px to 12-16px. The prompt boxes are compact (one row in
  the docked prompt). The breadcrumb, which repeats the top bar, is hidden. Fields are 16px so
  iOS does not zoom into them. Touch targets are at least 40px. Wide tables scroll sideways
  inside their frame. The welcome guide shows its steps as a strip and drops its preview art.
- **Tooltips** appear for mouse and keyboard only. A tap focuses its button, so a focus
  tooltip would linger.
- **Plain CSS media queries** in each component's styles file (ADR-024), with no new
  dependency.

## Consequences

- `web/e2e/mobile.spec.ts` (16 tests) covers it:
  - the drawer opens, closes and navigates;
  - no screen scrolls sideways at phone width, and in landscape;
  - the settings strip, the order of the action form, the 16px fields, and no tooltip on tap;
  - the tablet rail, and the desktop without the phone bar.
- The command palette is keyboard-only (Cmd+K), so phones do not reach it. Its screens are
  in the drawer; whether its other shortcuts need a touch entry is open.
