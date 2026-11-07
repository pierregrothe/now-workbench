# Story 2026.11d.01: Ratchet on dead identifiers in domain cards

Status: done
Started: 2026-11-07
Done: 2026-11-07
Spec-Clarity: high
Depends-On: none
Board: STORY-068

## Story

As an agent reading a domain card,
I want every code name it gives to exist,
so that I never wire into something that was renamed.

## Acceptance Criteria

AC1:
**Given** a card under `src/now_workbench/**/CLAUDE.md` names `` `SomeName` `` in backticks
**When** the ratchet runs
**Then** it counts the name as dead unless `src/now_workbench` defines it (def, class, parameter, assignment, attribute, identifier string, module or package name); builtins, stdlib and installed packages are exempt

AC2:
**Given** a name that is real but not code in src
**When** it is listed in `.ratchet/card_reference_allowlist.txt` with `# reason`
**Then** it is not counted; an entry without a reason is itself an error

AC3:
**Given** the baseline is 0
**When** a commit adds a dead name
**Then** `ratchet-all` blocks the commit

## Must NOT

- Must NOT read fenced code blocks or file names as identifiers
- Must NOT import or run project code

## Tasks / Subtasks

- [x] `.ratchet/count_card_dead_references.py` + allowlist (AC: 1,2)
- [x] Register `card-dead-references` in `ratchet_check.py`, baseline 0 (AC: 3)
- [x] Tests (AC: 1-3)

## Definition of Done

- [x] All acceptance criteria verified
- [x] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [x] Ruff clean (zero violations), mypy strict, tsc clean
- [x] No changes outside the story's stated scope
- [x] References section links verified

## References

- srv02chambly `alphaseeker/.ratchet/count_card_dead_references.py`
- ADR-033
