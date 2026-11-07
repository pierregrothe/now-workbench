# ADR-034: Otto Memory per Person

**Status:** accepted 2026-11-07
**Date:** 2026-11-07
**Builds on:** ADR-002 (Otto on the Claude API), ADR-020 (impersonation), ADR-023 (prompt
caching and budgets), ADR-028 (telemetry), ADR-031 (allowances)
**PRD:** `.primer/prd/PRD-004-otto-memory.md`
**Epic:** `.primer/epics/2026.11f-otto-memory/epic.md`

## Context

Otto starts every thread knowing nothing about the person. PRD-004 asks for per-person memory
that is extracted from conversations, owned and controlled by the person, and private.

## Decision

- **Storage:** a new `memory` domain with a `MemoryRepository(conn)`. It owns two tables:
  `memory_items` and `memory_state`.
  - `memory_items` columns: id, owner_email, kind, text, source_thread_id, source_message_id,
    origin (`extracted`, `told` or `computed`), hidden, use_count, created_at, updated_at.
  - `memory_state`, per owner: enabled, last_extracted_message_id.
  - Every read and write is gated on `current_owner()`. The schema version is the one after
    the feedback row's.
- **Kinds:** `preference`, `work`, `servicenow`, `style` and `other`. Each text is one fact of
  at most 280 characters, with no line breaks.
- **Extraction:**
  - A background task finds threads quiet for `memory_quiet_minutes` (a conversation limit,
    default 10) that have messages after the owner's last-extracted marker.
  - It sends those messages and the current items to Claude with model `claude-haiku-5-5`.
    The call goes through `interfaces/ai`, because the SDK may only be imported there.
  - It asks for JSON operations: `add` (kind, text), `update` (id, text) and `forget` (id).
  - Each run is capped at 10 operations. The secret filter drops any text that looks like a
    key, password, token, email address or long digit run.
  - Usage is recorded through `record_usage`, so it counts in the allowance.
  - It is skipped when memory is off, when the allowance is exhausted, or in simulation.
  - A failed call leaves the marker where it was, so the messages are tried again next time.
- **Computed items:** the same pass refreshes up to five `servicenow` items with
  origin `computed`, for the person's most-used tables, plugins and actions. They are counted
  from telemetry actions and the tool calls stored in messages. No model is involved. A
  person can hide them but not edit them.
- **Recall:** when a thread is created, the owner's visible items are rendered into a memory
  block and stored on the thread. The cap is 50 items and 4,000 characters, newest and most
  used first.
  - The block is sent as a second system block after Otto's cached system prompt, with its
    own cache breakpoint.
  - Because it is frozen per thread, every request in the thread sends the same bytes and
    the cache prefix holds (ADR-023).
  - Edits made during a thread take effect in the next thread.
- **Tools:** `remember` (origin `told`), `forget` (finds candidates, then deletes after the
  person confirms in words, ADR-026) and `my_memory`.
- **Control and visibility:**
  - Profile > Memory lists, edits, hides and deletes items, can delete them all, and has
    the on/off switch.
  - The API is owner-only; "view as" acts as the viewed person (ADR-020). There is no
    administrator route.

## Consequences

- The extraction cost is bounded: each pass sends only the new messages since the last one,
  plus the current items, to the cheapest model.
- A thread's memory can be stale for that one thread. That is accepted to keep caching intact.
- The secret filter is a pattern filter. It errs on dropping text, and the extraction prompt
  also tells the model not to propose secrets.
