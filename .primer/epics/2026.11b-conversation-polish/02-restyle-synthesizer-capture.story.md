# Story 2026.11b.02: Synthesizer and Media Capture in the Otto look

Status: backlog
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

- [ ] Measure gaps against ADR-019 and list them in the story (AC: 1)
- [ ] Restyle in the sibling styles files (AC: 1)
- [ ] Screenshot review at 1440, 820, 390 (AC: 1,2)

## Definition of Done

- [ ] All acceptance criteria verified
- [ ] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [ ] Ruff clean (zero violations), mypy strict, tsc clean
- [ ] No changes outside the story's stated scope
- [ ] References section links verified

## Existing Code

- `web/src/views/now-synthesizer-view.ts`, `now-capture-studio.ts`

## Dev Notes

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
