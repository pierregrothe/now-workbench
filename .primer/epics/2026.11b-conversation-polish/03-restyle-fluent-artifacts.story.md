# Story 2026.11b.03: Fluent Explorer and Artifact library cards in the Otto look

Status: done
Done: 2026-11-07
Started: 2026-11-07
Spec-Clarity: medium
Depends-On: none
Board: STORY-063

## Story

As a solution consultant,
I want the Fluent Explorer and Artifact library cards to match the Otto measurements,
so that the workbench looks like one product in demos.

## Acceptance Criteria

AC1:
**Given** both screens
**When** rendered at desktop and phone sizes
**Then** they follow ADR-019 measurements and Lux tokens and nothing scrolls sideways

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

- `web/src/components/now-fluent-explorer*.ts`, `now-demo-catalog*.ts`

## Dev Notes

### Gaps measured against ADR-019 (2026-11-07)

Reference: ADR-019 measurements, the Settings section menu, and the Synthesizer and Media
Capture screens restyled in story 02 (`web/src/styles/form-styles.ts`). Both screens shared:

- **Inline CSS** (ADR-024): 19 `style=` attributes in each component.
- **Canvas**: both used `--now-bg-canvas` (`#f8fafc`, cool slate) instead of the Otto canvas
  `#efece7` (`--otto-canvas`); 24px/32px gutters instead of the workspace's 24px/36px.
- **Screen titles** 16-20px bold; the restyled screens use 24px medium (20px on phones).
- **Text contrast under WCAG AA (4.5:1)**: the Fluent "-" and "Optional" cells `#94a3b8` on
  white (2.6:1); the library import button, white on the brand green (3.25:1); the release
  badge and media-type badge `#16a34a` on `#f0fdf4` (3.15:1); the "Download" link `#16a34a`;
  the Fluent schema error `#dc2626` on the canvas (4.1:1).
- **Touch targets** (ADR-030) under 40px on phones: the Fluent icon buttons (32px), copy
  button (28px) and bundle picker (about 28px, 12.5px text so iOS zooms into it); the
  library card buttons and import button (36px), "View Proofs" (about 22px) and the
  notification close (about 20px).

Fluent Explorer only:

- A white header bar with a bottom border; ADR-019's top bar blends into the canvas.
- The tables list was a white rail with a border and green-tinted chosen row; Otto's section
  menus (Settings) are a white 16px card with 10px rows and a dark `#1a1a1a` chosen row.
- Cards radius 10px; the workspace cards are 16px with a soft shadow.
- Blue and slate pills with 4px corners, uppercase letter-spaced headers; the code box used
  generic `monospace` and a hard-coded slate instead of `--now-font-mono`/`--now-radius-md`.
- The bundle picker was an inline-styled 6px select, not the shared 10px `.select-input`.

Artifact library only:

- Its own square `.btn-primary` (radius 6px), not the shared AA pill.
- Card icon buttons square (6px); cool slate tag pills and media bar with borders; the card
  metadata row did not wrap.

### What changed

- CSS moved from `style=` attributes into `now-fluent-explorer-styles.ts`,
  `now-demo-catalog-styles.ts` and a new `now-demo-catalog-modal-styles.ts` (the modal rules,
  split out to keep each file under 500 lines). Both screens use `formStyles`: the bundle
  picker is `.select-input`, the import button the shared `.btn-primary` pill.
- Otto canvas and gutters, 24px/500 titles, 16px white cards, warm `#f4f3f0` chips and
  table headers, round icon buttons, the Settings-style tables menu (a strip at 900px or
  less), and the AA colours above (`--now-text-muted`, `#047857`, `#b42318`).
- The deploy and clone dialogs reuse `demoCatalogStyles`, so their primary button is now the
  shared AA pill colours too (dark text on the brand green); their layout is unchanged. On
  phones their icon buttons are 40x40 so siblings match, and their 32px close button is the
  shared `.modal-close` class instead of an inline style.
- No text, accessible name, role, event handler or API call changed.
- `web/e2e/mobile.spec.ts`: a phone test asserts every button of both screens is at least
  40x40px, the Fluent bundle picker is 16px and 40px tall, and neither screen scrolls sideways.
  Because each screen scrolls inside its own host, a new `expectNoSidewaysScrollIn` helper also
  checks the host and every scroll container in its shadow trees, except the frames meant to
  scroll sideways (Fluent: the tables strip, the table card, the code box). The VIEWS loop keeps
  the page-level check: its other screens have not been audited for such frames.
- Review fixes: the table id keeps 5.8:1 on the row hover; the proofs "Clear All"/"Delete" text
  is `#b42318`; the proofs links are 40px tall on phones; the code box reserves a row above the
  code for the 40px copy button on phones (top padding rather than right padding, since a long
  first line scrolls under a right-hand button anyway).

### Modules Affected

- web/src/components/now-fluent-explorer.ts (+ styles file)
- web/src/components/now-demo-catalog.ts (+ styles file, new modal styles file)

### Testing Approach

- Existing Playwright specs; mobile.spec.ts

### Conventions

- No mocks: in-memory fakes, `httpx.MockTransport`, `monkeypatch.setattr` of functions (project precedent).
- Mutation-gated modules (`[tool.mutmut]`) must keep every mutant killed (ADR-029).
- Web: CSS in a sibling `*-styles.ts`, store through `StoreController` (ADR-024); phone rules at `(max-width: 768px), (max-height: 500px)` (ADR-030).

## References

- ADR: `.primer/adr/ADR-019-otto-look-and-feel-alignment.md`
- PRD: `.primer/prd/PRD-002-otto-conversation-and-tiles.md`
- Source: owner backlog review 2026-11-07 (active.md Next Steps / Known Issues)
