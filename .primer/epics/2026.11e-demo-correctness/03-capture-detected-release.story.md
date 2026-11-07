# Story 2026.11e.03: Capture uses the detected release

Status: done
Started: 2026-11-07
Done: 2026-11-07
Spec-Clarity: high
Depends-On: none
Board: STORY-074

## Acceptance Criteria

AC1:
**Given** an instance whose detected release is not Xanadu
**When** a capture runs from the API, Otto or a video playbook
**Then** workspace paths are translated for that release; no code path defaults to "Xanadu"

AC2:
**Given** an instance whose release is unknown
**When** a capture runs
**Then** it says the release is unknown instead of guessing (ADR-014)

## Tasks / Subtasks

- [x] Reproduce with a failing test first, then fix (AC: 1-2)
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
