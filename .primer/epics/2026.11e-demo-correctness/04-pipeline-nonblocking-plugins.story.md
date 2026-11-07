# Story 2026.11e.04: Plugin queries off the event loop

Status: done
Started: 2026-11-07
Done: 2026-11-07
Spec-Clarity: high
Depends-On: none
Board: STORY-075

## Acceptance Criteria

AC1:
**Given** the async demo pipeline
**When** it evaluates or installs plugins
**Then** the synchronous HTTP plugin queries run off the event loop (another request is served meanwhile)

## Tasks / Subtasks

- [x] Reproduce with a failing test (event loop blocked), then fix (AC: 1)
- [x] Update the affected domain card(s) so they no longer list the fixed gotcha

## Definition of Done

- [x] All acceptance criteria verified
- [x] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [x] Ruff clean (zero violations), mypy strict, tsc clean
- [x] No changes outside the story's stated scope
- [x] References section links verified

## References

- Domain cards under `src/now_workbench/domains/*/CLAUDE.md` (gotchas) and PR #4
- `.primer/epics/2026.11e-demo-correctness/epic.md`
