# Story 2026.11b.05: Tests mirror the platform / domains / interfaces layout

Status: backlog
Spec-Clarity: high
Depends-On: none
Board: STORY-065

## Story

As a developer,
I want tests under `tests/platform`, `tests/domains`, `tests/interfaces`,
so that the test for a module is easy to find.

## Acceptance Criteria

AC1:
**Given** the test suite
**When** files are moved by layer
**Then** the same tests run (count unchanged), coverage stays 100%, and the mutation gate's test selection is updated

## Must NOT

- Must NOT change any test's logic while moving it
- Must NOT split files beyond the move

## Tasks / Subtasks

- [ ] Map each test file to a layer (AC: 1)
- [ ] git mv, fix imports/conftest, update [tool.mutmut] selection (AC: 1)
- [ ] Run full suite and gate (AC: 1)

## Definition of Done

- [ ] All acceptance criteria verified
- [ ] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [ ] Ruff clean (zero violations), mypy strict, tsc clean
- [ ] No changes outside the story's stated scope
- [ ] References section links verified

## Existing Code

- `tests/` -- 68 flat files

## Dev Notes

### Modules Affected

- tests/
- pyproject.toml ([tool.mutmut])

### Testing Approach

- pytest count before/after equal; mutation gate passes

### Conventions

- No mocks: in-memory fakes, `httpx.MockTransport`, `monkeypatch.setattr` of functions (project precedent).
- Mutation-gated modules (`[tool.mutmut]`) must keep every mutant killed (ADR-029).
- Web: CSS in a sibling `*-styles.ts`, store through `StoreController` (ADR-024); phone rules at `(max-width: 768px), (max-height: 500px)` (ADR-030).

## References

- ADR: `.primer/adr/ADR-015-domain-oriented-package-architecture.md`
- Source: owner backlog review 2026-11-07 (active.md Next Steps / Known Issues)
