# Story 2026.11a.06: Otto's follow-ups know what tools he used

Status: done
Done: 2026-11-07
Started: 2026-11-07
Spec-Clarity: medium
Depends-On: none
Board: STORY-059

## Story

As a person talking to Otto,
I want Otto's follow-up answers to describe his earlier tool use correctly,
so that he does not deny or invent what he already did.

## Acceptance Criteria

AC1:
**Given** a reply produced by the agent loop with tool calls
**When** the next question is sent
**Then** the Claude request contains that reply's tool_use and tool_result blocks (stored transcript)

AC2:
**Given** a reply produced by the legacy stream path or before transcripts existed
**When** the next question is sent
**Then** the request carries an explicit note of the tools used, or the gap is documented as accepted

AC3:
**Given** the known-issues list
**When** the story is done
**Then** the item is removed or narrowed to the remaining case

## Must NOT

- Must NOT break prompt caching of the history prefix
- Must NOT replay tool calls

## Tasks / Subtasks

- [x] Prove with a test that stored transcripts reach the next request (agent_transcript exists since an earlier ADR) (AC: 1)
- [x] Close the remaining gap for the legacy path, if any (AC: 2)
- [x] Update active.md known issues (AC: 3)

## Definition of Done

- [x] All acceptance criteria verified
- [x] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [x] Ruff clean (zero violations), mypy strict, tsc clean
- [x] No changes outside the story's stated scope
- [x] References section links verified

## Existing Code

- `src/now_workbench/domains/conversations/repository.py` -- `agent_transcript` column and `list_transcripts`
- `src/now_workbench/interfaces/ai/conversation.py` `_history_to_messages`

## Dev Notes

### Modules Affected

- src/now_workbench/interfaces/ai/conversation.py
- src/now_workbench/interfaces/ai/client.py

### Outcome (2026-11-07)

- AC1 was already true: `replay_conversation` replays stored transcripts, proven by `test_post_thread_message_replays_the_previous_exchange_byte_for_byte` (asserts the tool_use block).
- The real gap was confirmed actions: stored as a bare result with no transcript. They now store "I ran `<tool>` after you confirmed. <result>" (or "tried to run" on failure) as their transcript; the person still sees only the result.
- Accepted gap: the `/ws/otto` WebSocket agent path (not used by the web UI) still sends history as text only.

### Testing Approach

- Fake Anthropic client capturing the request; assert tool blocks present

### Conventions

- No mocks: in-memory fakes, `httpx.MockTransport`, `monkeypatch.setattr` of functions (project precedent).
- Mutation-gated modules (`[tool.mutmut]`) must keep every mutant killed (ADR-029).
- Web: CSS in a sibling `*-styles.ts`, store through `StoreController` (ADR-024); phone rules at `(max-width: 768px), (max-height: 500px)` (ADR-030).

## References

- ADR: `.primer/adr/ADR-023-prompt-caching-compaction-and-token-budgets.md` (stored transcripts), `.primer/adr/ADR-025-otto-tool-set-and-visual-tiles.md`
- Known issue: Otto's follow-up replies can misreport their own tool use
- Source: owner backlog review 2026-11-07 (active.md Next Steps / Known Issues)
