# Story 2026.11f.03: Recall, computed areas and Otto's memory tools

Status: backlog
Spec-Clarity: high
Depends-On: 01
Board: STORY-079

## Acceptance Criteria

AC1:
**Given** a new thread
**When** its first request goes to Claude
**Then** a memory block (visible items, max 50 items / 4,000 characters) follows the cached system prompt, and every later request in the thread sends it byte-identical

AC2:
**Given** memory off
**When** a thread starts
**Then** no memory block is sent

AC3:
**Given** telemetry and stored tool calls
**When** the pass refreshes computed items
**Then** up to five `servicenow` items name the person's most-used tables, plugins and actions

AC4:
**Given** a conversation
**When** the person asks Otto to remember, forget, or show its memory
**Then** `remember`, `forget` (confirmed in words) and `my_memory` do it

## Tasks / Subtasks

- [ ] Freeze the block on the thread; second system block with its own breakpoint (AC: 1,2)
- [ ] Computed items from telemetry and tool calls (AC: 3)
- [ ] Otto tools + confirmation (AC: 4)
- [ ] Tests with the fake client (AC: 1-4)

## Definition of Done

- [ ] All acceptance criteria verified
- [ ] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [ ] Ruff clean (zero violations), mypy strict, tsc clean
- [ ] No changes outside the story's stated scope
- [ ] References section links verified

## References

- PRD: `.primer/prd/PRD-004-otto-memory.md`
- ADR-034, ADR-023, ADR-031
