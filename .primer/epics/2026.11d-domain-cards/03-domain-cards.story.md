# Story 2026.11d.03: A card for each of the 19 domains

Status: backlog
Spec-Clarity: high
Depends-On: 01
Board: STORY-070

## Story

As an agent working in a domain,
I want a short card that Claude loads automatically,
so that I use the domain's public root, repository and invariants instead of guessing.

## Acceptance Criteria

AC1:
**Given** each of the 19 domains in `src/now_workbench/domains/`
**When** its card is read
**Then** it follows one format: what the domain does (and does not), public entry points from `now_workbench.domains.<name>`, wiring (repository, `db_session`, who imports it), invariants and gotchas, do not reinvent

AC2:
**Given** every card
**When** the dead-reference ratchet runs
**Then** it counts 0

AC3:
**Given** every card
**When** a reviewer checks it against the code
**Then** each claim holds or is fixed

## Must NOT

- Must NOT exceed about 120 lines per card
- Must NOT restate project-wide rules from the root CLAUDE.md

## Tasks / Subtasks

- [ ] Write the 19 cards (AC: 1)
- [ ] Ratchet at 0 (AC: 2)
- [ ] Independent review against the code (AC: 3)

## Definition of Done

- [ ] All acceptance criteria verified
- [ ] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [ ] Ruff clean (zero violations), mypy strict, tsc clean
- [ ] No changes outside the story's stated scope
- [ ] References section links verified

## References

- srv02chambly `alphaseeker/src/alphaseeker/services/journal/CLAUDE.md` (exemplar)
- ADR-015
- ADR-033
