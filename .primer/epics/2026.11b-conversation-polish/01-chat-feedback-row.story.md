# Story 2026.11b.01: Thumbs up/down and Get help under Otto's replies

Status: backlog
Spec-Clarity: high
Depends-On: none
Board: STORY-061

## Story

As a person talking to Otto,
I want to rate a reply and ask for help from under it,
so that the owner learns which answers fail.

## Acceptance Criteria

AC1:
**Given** an Otto reply
**When** the person taps thumbs up or down (optionally with a comment)
**Then** the rating is stored with the message, the person and the time, and the button shows the choice

AC2:
**Given** a rated reply
**When** the person changes the rating
**Then** the stored rating is replaced, not duplicated

AC3:
**Given** an administrator
**When** they open the feedback list
**Then** they see ratings with the reply text; consultants see only their own

AC4:
**Given** Get help
**When** it is tapped
**Then** it opens the help guide (no external service)

## Must NOT

- Must NOT send feedback outside the workbench
- Must NOT rate user messages

## Tasks / Subtasks

- [ ] Schema + repository for message feedback (owner-scoped) (AC: 1,2,3)
- [ ] API endpoints (AC: 1,2,3)
- [ ] Feedback row in the chat view (phone sizes too) (AC: 1,2,4)
- [ ] Tests: pytest + Playwright (AC: 1-4)

## Definition of Done

- [ ] All acceptance criteria verified
- [ ] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [ ] Ruff clean (zero violations), mypy strict, tsc clean
- [ ] No changes outside the story's stated scope
- [ ] References section links verified

## Existing Code

- `web/src/views/now-chat-view.ts` -- reply rendering
- PRD-002 feedback row (not built)

## Dev Notes

### Modules Affected

- src/now_workbench/platform/db/schema.py
- src/now_workbench/domains/conversations/
- src/now_workbench/interfaces/api/threads.py
- web/src/views/now-chat-view.ts

### Testing Approach

- Repository + API tests; Playwright rate/change/admin list

### Conventions

- No mocks: in-memory fakes, `httpx.MockTransport`, `monkeypatch.setattr` of functions (project precedent).
- Mutation-gated modules (`[tool.mutmut]`) must keep every mutant killed (ADR-029).
- Web: CSS in a sibling `*-styles.ts`, store through `StoreController` (ADR-024); phone rules at `(max-width: 768px), (max-height: 500px)` (ADR-030).

## References

- PRD: `.primer/prd/PRD-002-otto-conversation-and-tiles.md`
- Source: owner backlog review 2026-11-07 (active.md Next Steps / Known Issues)
