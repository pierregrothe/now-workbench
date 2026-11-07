# ADR-024: Web Component Structure -- Styles, Controllers and Sub-Components

**Status:** accepted 2026-11-07
**Date:** 2026-11-07
**Follows:** ADR-015 Q4 (web components get their own ADR after the Python restructure)
**Amends:** ADR-010 (modular web components), ADR-005 (web file-size limit)

## Context

`web/src` has 13,700 lines of Lit components. Eight files exceed the 500-line limit
(largest 1,559) and are held in `.file-size-baseline.json`. Measured 2026-11-07:

- **Styles dominate.** Inline `static styles` is 40-60% of the largest files (728 of
  1,559 lines in the admin panel, 621 of 1,123 in the demo catalog).
- **Copied lifecycle code.** Five components subscribe to `workbenchStore` by hand in
  `connectedCallback` and unsubscribe in `disconnectedCallback`.
- **Copied markup.** The chat, capture-studio and synthesizer views each carry the same top
  bar (breadcrumb, instance picker, load-error badge).
- **Dead code.** `now-otto-drawer` (478 lines) is mounted nowhere; the chat view replaced it.

## Decision

1. **Styles live beside their component.** A component's CSS goes in
   `<component>-styles.ts` exporting a `css` constant (the pattern `chat-view-styles.ts`
   already uses). Rules repeated across components (field labels, buttons, cards) go in
   `styles/` partials that components compose: `static styles = [shared, own]`.
2. **Store access through one controller.** `StoreController` (a Lit `ReactiveController`)
   subscribes on connect, re-renders the host on change and unsubscribes on disconnect.
   Components read `this.store.state`; nobody calls `workbenchStore.subscribe` directly.
3. **Shared chrome is a component.** The views' top bar becomes `<now-workspace-bar>`.
4. **Big components split by section.** A component above 500 lines after its styles moved
   out is divided into child elements, one per screen section (for example each admin
   panel tab), each owning its state and requests. Parents pass data down by property and
   hear back through events.
5. **The 500-line limit blocks with no baseline.** The eight entries leave
   `.file-size-baseline.json` as each file comes under the limit; the baseline ends empty.
6. **Dead components are deleted**, not kept for reference.

## Migration status (2026-11-07)

Done: `StoreController` replaces the five hand-written subscriptions; `<now-workspace-bar>`
replaces three copied top bars; every large component's CSS moved to `*-styles.ts`; the
admin panel, settings, demo catalog and shell were split (hero, add form, diagnostics,
preference sections on a `PrefsSection` base, clone and deploy dialogs,
`ThreadListController`, a pure `detectIntent`); one `InstanceData` type in
`context/instance-model.ts`; `now-otto-drawer` deleted. `.file-size-baseline.json` is gone:
every web file is under 500 lines. Fixed on the way (ADR-013): diagnostics no longer
invent values, and failed settings, bundle and conversation loads are reported instead of
showing defaults or empty lists. Left as is: the capture-studio and synthesizer form CSS
look alike but differ in spacing, so merging them would change the screens.

## Consequences

- Components shrink to behaviour and markup; CSS changes stay in one file per component.
- Lifecycle leaks (a listener left behind by a forgotten unsubscribe) cannot recur in the
  components that use the controller.
- Split sections are independently testable; e2e selectors keep working because markup and
  element names inside each section stay the same.
