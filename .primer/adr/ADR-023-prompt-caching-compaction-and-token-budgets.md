# ADR-023: Prompt caching, compaction and per-conversation token budgets

**Status:** accepted
**Date:** 2026-11-06
**Supersedes:** the question cap of ADR-021 (its age and file limits remain)

## Context

The owner asked to cache prompts aggressively to save tokens. They also asked to replace the
per-conversation question cap with a token budget and automatic compaction. The audit found
that only tools and the system prompt were cached:
- each follow-up question rebuilt the conversation from text summaries, a different prefix
  from what Claude had seen;
- a 20-message sliding window moved the start of the conversation;
- attachments were re-sent uncached on every question.

## Decision

- **Append-only replay.** Each Otto reply stores its exact Claude transcript: tool calls,
  tool results, compaction blocks and the final answer (`chat_messages.agent_transcript`,
  schema v12). Later questions replay the whole conversation byte for byte
  (`replay_conversation`), with no sliding window. User turns are rebuilt the way they were
  sent (files, then text). Append-only history also satisfies the preserved-thinking check.
- **Cache layout.**
  - Tools (sorted by name) and the frozen system prompt form one prefix. It has an explicit
    1-hour breakpoint on the system block and is shared by every conversation.
  - Automatic caching (top-level `cache_control`) moves a 5-minute breakpoint along the
    conversation.
  - Requests carry a snapshot of the message list, never a live reference.
- **Server-side compaction** (beta `compact-2026-01-12`, `compact_20260112`). It triggers at
  an admin-set input size: default 150,000, minimum 50,000. Its instructions keep goals, ids
  and pending work, and forbid tool calls while summarizing. The compaction block is stored and
  replayed like any other block.
- **Token budget per conversation.** Every reply adds its billable tokens to the
  conversation (`chat_threads.tokens_used`): fresh input + output + 1.25 x cache writes +
  0.1 x cache reads, compaction iterations included. A conversation that reached
  `max_conversation_tokens` (default 2,000,000, admin-set) accepts no new questions;
  confirmations still go through. The sidebar shows used/budget.
- **Visible usage.** Each reply's usage is in its widget data and in the server log
  ("Otto usage ... cache_read=... billable=..."), so cache hits can be verified in production.
  `tests/test_prompt_caching.py` fails if a change breaks the byte-identical replay or the
  markers.

## Consequences

- Transcripts can be large: tool results with screenshots are kept until the conversation is
  deleted.
- Compaction costs a summarization call (counted in the budget). It resets the conversation
  cache once; the tools and system cache survive.
