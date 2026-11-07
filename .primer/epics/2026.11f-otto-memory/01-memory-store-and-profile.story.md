# Story 2026.11f.01: Memory store, API and Profile > Memory

Status: backlog
Spec-Clarity: high
Depends-On: EPIC-018/01
Board: STORY-077

## Acceptance Criteria

AC1:
**Given** the `memory` domain
**When** a person's items are read or written
**Then** only that owner's rows are touched (`current_owner()`); another person, an administrator included, sees none

AC2:
**Given** Profile > Memory
**When** the person opens it
**Then** they see every item with its kind and origin, and can edit (not computed ones), hide, delete, delete all, and turn memory off

AC3:
**Given** an item text
**When** it is saved by any path
**Then** it is one line of at most 280 characters, and text that looks like a secret is refused

## Tasks / Subtasks

- [ ] Schema migration + `MemoryRepository` + service (AC: 1,3)
- [ ] API routes, owner-only (AC: 1,2)
- [ ] Profile > Memory UI, phone sizes (AC: 2)
- [ ] Domain card for `memory` (AC: 1)
- [ ] pytest + Playwright (AC: 1-3)

## Definition of Done

- [ ] All acceptance criteria verified
- [ ] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [ ] Ruff clean (zero violations), mypy strict, tsc clean
- [ ] No changes outside the story's stated scope
- [ ] References section links verified

## References

- PRD: `.primer/prd/PRD-004-otto-memory.md`
- ADR-034, ADR-023, ADR-031
