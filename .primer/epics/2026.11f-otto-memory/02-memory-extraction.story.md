# Story 2026.11f.02: Background extraction

Status: backlog
Spec-Clarity: high
Depends-On: 01
Board: STORY-078

## Acceptance Criteria

AC1:
**Given** a thread quiet for `memory_quiet_minutes` (default 10) with new messages
**When** the background pass runs
**Then** it sends only the new messages and current items to `claude-haiku-5-5`, applies at most 10 add/update/forget operations, advances the marker, and records the usage

AC2:
**Given** memory off, an exhausted allowance, or simulation
**When** the pass would run
**Then** it does not call Claude

AC3:
**Given** a failed call or a malformed reply
**When** the pass ends
**Then** nothing is applied and the marker stays, so the messages are retried

AC4:
**Given** a proposed item that looks like a secret
**When** it is applied
**Then** it is dropped

## Tasks / Subtasks

- [ ] Extraction prompt + JSON contract in interfaces/ai (AC: 1,4)
- [ ] Scheduler for quiet threads (AC: 1,2)
- [ ] Fake-client tests incl. failures and secrets (AC: 1-4)

## Definition of Done

- [ ] All acceptance criteria verified
- [ ] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [ ] Ruff clean (zero violations), mypy strict, tsc clean
- [ ] No changes outside the story's stated scope
- [ ] References section links verified

## References

- PRD: `.primer/prd/PRD-004-otto-memory.md`
- ADR-034, ADR-023, ADR-031
