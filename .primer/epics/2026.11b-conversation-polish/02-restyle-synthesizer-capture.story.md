# Story 2026.11b.02: Synthesizer and Media Capture in the Otto look

Status: done
Done: 2026-11-07
Started: 2026-11-07
Spec-Clarity: medium
Depends-On: none
Board: STORY-062

## Story

As a solution consultant,
I want the Synthesizer and Media Capture screens to match the Otto measurements,
so that the workbench looks like one product in demos.

## Acceptance Criteria

AC1:
**Given** both screens
**When** rendered at desktop and phone sizes
**Then** cards, type, spacing and buttons use the ADR-019 measurements and Lux tokens, and nothing scrolls sideways

AC2:
**Given** existing behaviour
**When** the screens are used
**Then** every Playwright spec still passes

## Must NOT

- Must NOT change behaviour or API calls
- Must NOT add a CSS framework

## Tasks / Subtasks

- [x] Measure gaps against ADR-019 and list them in the story (AC: 1)
- [x] Restyle in the sibling styles files (AC: 1)
- [x] Screenshot review at 1440, 820, 390 (AC: 1,2) -- done in the orchestrator's gate, with the Playwright run

## Definition of Done

- [x] All acceptance criteria verified
- [x] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [x] Ruff clean (zero violations), mypy strict, tsc clean
- [x] No changes outside the story's stated scope
- [x] References section links verified

## Existing Code

- `web/src/views/now-synthesizer-view.ts`, `now-capture-studio.ts`

## Dev Notes

### Gaps measured against ADR-019 (2026-11-07)

Reference: ADR-019 measurements and the screens already in the Otto look (chat view prompt box,
Settings cards, fields, pill buttons and dark-chip section menu). Both views shared these gaps:

- **CSS inline in the component** (ADR-024): `static styles` held 110-170 lines, and the markup
  carried eleven `style=` attributes (result header, titles, badges, empty states, play glyph).
- **Field labels** 11.5-12px, uppercase, letter-spaced, secondary grey; Otto/Settings use
  12.5px semibold sentence case in the primary text colour.
- **Fields** radius 6px, 13px text, 8px/12px padding, no focus colour; Settings uses radius
  10px, 13.5px, 9px/12px, brand-green focus border.
- **Primary buttons** square-ish (radius 6px), weight 700, navy through `--now-color-primary`,
  a token `lux-theme.css` does not define; the restyled screens use pills
  (`--now-radius-pill`) in `--now-color-brand-green`.
- **Touch targets** (ADR-030) under 40px on phones: the primary buttons (about 36px), the
  result tabs, the capture-mode buttons and the gallery's small buttons (about 22px).
- **Sideways-scroll risks**: the synthesizer result header (title + seed button) did not wrap;
  the tab bar did not wrap; the gallery minimum column (280px) and the `1fr` result column
  could outgrow a narrow frame.

Synthesizer only:

- The use-case objective is the screen's prompt but was 13px text in a 6px box; ADR-019 gives
  16px/24px text in a softly rounded box with the warm `#f4f3f0` ring.
- Result tabs were underline tabs in navy; Otto's selectors are warm chips with a dark
  (`#1a1a1a`) chosen item, as the Settings menu.
- Code preview used a hard-coded colour and generic `monospace`, radius 8px, instead of
  `--now-font-mono` and `--now-radius-md`.

Media Capture only:

- Capture-mode toggle was two bordered 6px buttons with a navy fill; now the same warm
  segmented chips as the synthesizer tabs.
- Artifact cards radius 8px with a grey `--now-bg-surface-1` action strip and a navy
  thumbnail ground; the workspace cards are radius 16px white with a soft shadow.
- Small buttons radius 4px, 11px text; danger colour hard-coded instead of
  `--now-status-error`.
- The gallery heading was 15px; card and section titles elsewhere are 16px/700.

### What changed

- CSS moved to `now-synthesizer-view-styles.ts` and `now-capture-studio-styles.ts` and
  restyled to the points above; inline `style=` attributes became classes. No markup structure,
  text, accessible name, event handler or API call changed.
- `web/e2e/mobile.spec.ts`: one phone test asserts the synthesizer and capture buttons are at
  least 40px tall and the objective field is 16px.

### Modules Affected

- web/src/views/now-synthesizer-view.ts
- web/src/views/now-capture-studio.ts (+ styles files)

### Testing Approach

- Existing Playwright specs; phone-fit checks in mobile.spec.ts

### Conventions

- No mocks: in-memory fakes, `httpx.MockTransport`, `monkeypatch.setattr` of functions (project precedent).
- Mutation-gated modules (`[tool.mutmut]`) must keep every mutant killed (ADR-029).
- Web: CSS in a sibling `*-styles.ts`, store through `StoreController` (ADR-024); phone rules at `(max-width: 768px), (max-height: 500px)` (ADR-030).

## References

- ADR: `.primer/adr/ADR-019-otto-look-and-feel-alignment.md`
- PRD: `.primer/prd/PRD-002-otto-conversation-and-tiles.md`
- Source: owner backlog review 2026-11-07 (active.md Next Steps / Known Issues)
