# Story 2026.11a.01: Monthly Claude usage allowance per person, enforced

Status: backlog
Spec-Clarity: high
Depends-On: none
Board: STORY-054

## Story

As the workbench owner,
I want each non-admin person to have a monthly allowance of billable Claude tokens that Otto enforces,
so that outside testers cannot run up an unbounded bill on my Claude key.

## Acceptance Criteria

AC1:
**Given** a consultant whose billable tokens this UTC month are below 80% of their allowance
**When** they ask Otto a question
**Then** Otto answers normally and no warning is shown

AC2:
**Given** a consultant at or above 80% but below 100%
**When** they ask a question
**Then** the reply carries a warning naming the percentage used and the reset date (1st of next month, UTC)

AC3:
**Given** a consultant at or above 100%
**When** they ask a question (chat, WebSocket or legacy stream)
**Then** no Claude call is made, the API answers 429 with a plain message naming the reset date, and no usage event is recorded

AC4:
**Given** an administrator, or the owner in local mode
**When** they are over any allowance
**Then** they are never refused (admins are exempt)

AC5:
**Given** an administrator viewing as a consultant
**When** the consultant's allowance is exhausted
**Then** the request is refused on the consultant's allowance, as the consultant would see it

## Must NOT

- Must NOT count tokens differently from the conversation budget (cache read 0.1, cache write 1.25; ADR-023)
- Must NOT call Claude to find out whether a person is over their allowance
- Must NOT refuse administrators

## Tasks / Subtasks

- [ ] Telemetry: billable tokens this month per owner (repository aggregate, mutation-gated) (AC: 1,2,3)
- [ ] Domain service `check_allowance(conn, user, now)` returning ok / warn / refused with percentage and reset date (AC: 1,2,3,4,5)
- [ ] Enforce at every Claude entry point (thread messages, WebSocket, legacy stream) before the call (AC: 3)
- [ ] Surface the warning on the reply and the 429 message in the chat view (AC: 2,3)
- [ ] Tests: service table tests, API 429, guard test that every Claude entry point checks the allowance (AC: 1-5)

## Definition of Done

- [ ] All acceptance criteria verified
- [ ] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [ ] Ruff clean (zero violations), mypy strict, tsc clean
- [ ] No changes outside the story's stated scope
- [ ] References section links verified

## Existing Code

- `src/now_workbench/domains/telemetry/` -- usage_events per owner (ADR-028)
- `src/now_workbench/domains/conversations/limits.py` -- per-conversation token budget (ADR-023)
- `src/now_workbench/interfaces/ai/agent.py` `_AgentLoop.absorb` -- records usage

## Dev Notes

### Modules Affected

- src/now_workbench/domains/telemetry/{repository,service}.py
- src/now_workbench/domains/settings/ (allowance storage, shared with story 02)
- src/now_workbench/interfaces/api/{threads,app}.py
- web/src/views/now-chat-view.ts

### Testing Approach

- Table tests of check_allowance at 0%, 79.9%, 80%, 99.9%, 100% and for admins
- API test: 429 body and no usage row written
- Architecture guard test like `test_claude_is_called_only_where_usage_is_recorded`

### Conventions

- No mocks: in-memory fakes, `httpx.MockTransport`, `monkeypatch.setattr` of functions (project precedent).
- Mutation-gated modules (`[tool.mutmut]`) must keep every mutant killed (ADR-029).
- Web: CSS in a sibling `*-styles.ts`, store through `StoreController` (ADR-024); phone rules at `(max-width: 768px), (max-height: 500px)` (ADR-030).

## References

- ADR: `.primer/adr/ADR-028-telemetry-and-live-instance-charts.md`
- ADR: `.primer/adr/ADR-023-prompt-caching-compaction-and-token-budgets.md` (token budgets)
- ADR: new ADR-031 (usage allowances)
- Source: owner backlog review 2026-11-07 (active.md Next Steps / Known Issues)
