# Story 2026.11e.05: Sharing and group rules hold

Status: backlog
Spec-Clarity: high
Depends-On: none
Board: STORY-076

## Acceptance Criteria

AC1:
**Given** an approved version whose zip is missing
**When** a bundle is resolved through the API
**Then** the answer is 404, not 500

AC2:
**Given** two saves of a new version at once
**When** both complete
**Then** each row's version matches its zip

AC3:
**Given** `workbench demo delete` from the CLI
**When** it removes a bundle
**Then** the sharing registry entry and version files go too, as in the API and Otto

AC4:
**Given** a group with one admin
**When** a group admin demotes or removes the last admin, or demotes another admin
**Then** it is refused; only a workbench administrator may demote a group admin

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
