# Story 2026.11e.01: One simulated-instance rule; no real deploy from fake mode

Status: done
Started: 2026-11-07
Done: 2026-11-07
Spec-Clarity: high
Depends-On: none
Board: STORY-072

## Acceptance Criteria

AC1:
**Given** an instance whose URL is `fake://...` or `http://fake...`, or the fake-mode setting
**When** any caller (pipeline deploy, Otto operations, seed API, capture) asks whether it is simulated
**Then** they all use one exported predicate from the instances domain and get the same answer

AC2:
**Given** a bundle with `package.json` deployed to a simulated instance with fake mode off
**When** `deploy_and_seed` runs
**Then** no real SDK deploy is attempted (it simulates, as for bundles without package.json)

AC3:
**Given** the seed API
**When** a request arrives
**Then** fake mode is the request flag OR the `sdk_fake_mode` preference OR a simulated instance, never less

## Tasks / Subtasks

- [x] Reproduce each defect with a failing test first, then fix (AC: 1-3)
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
