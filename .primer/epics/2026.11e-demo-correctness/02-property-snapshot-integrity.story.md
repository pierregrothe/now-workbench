# Story 2026.11e.02: Property snapshots keep the originals; restore reports failure

Status: backlog
Spec-Clarity: high
Depends-On: none
Board: STORY-073

## Acceptance Criteria

AC1:
**Given** an apply that fails partway
**When** it stops
**Then** the snapshot already holds the original of every property it changed

AC2:
**Given** a bundle applied twice without a restore
**When** the second apply runs
**Then** the first snapshot (the true originals) is kept, not overwritten

AC3:
**Given** a restore where any update fails, or a property the apply created
**When** restore runs
**Then** it reports failure with the names, keeps the snapshot, and deletes created properties (or reports them)

AC4:
**Given** a property name with reserved characters, or a caller-supplied client
**When** the engine queries or finishes
**Then** the name is URL-encoded and the caller's client is not closed

## Tasks / Subtasks

- [ ] Reproduce each defect with a failing test first, then fix (AC: 1-4)
- [ ] Update the affected domain card(s) so they no longer list the fixed gotcha

## Definition of Done

- [ ] All acceptance criteria verified
- [ ] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [ ] Ruff clean (zero violations), mypy strict, tsc clean
- [ ] No changes outside the story's stated scope
- [ ] References section links verified

## References

- Domain cards under `src/now_workbench/domains/*/CLAUDE.md` (gotchas) and PR #4
- `.primer/epics/2026.11e-demo-correctness/epic.md`
