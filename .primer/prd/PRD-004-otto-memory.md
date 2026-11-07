---
id: PRD-004
title: Otto memory per person
status: accepted
date: 2026-11-07
adrs: [ADR-002, ADR-020, ADR-023, ADR-028, ADR-031, ADR-034]
charter_link: charter.md#1-vision--purpose
milestone: unscheduled
---

# PRD-004: Otto memory per person

## Problem

Otto forgets everything between conversations. Each person has to repeat who they are, what
they work on, which instance and ServiceNow areas they care about, and how they like answers.
Remembering this per person makes Otto useful from the first message of a new thread.

## Users

- Consultants and administrators who talk to Otto: they benefit from it, and they see and
  control their own memory.
- Otto: it reads the memory at the start of a thread and can remember or forget on request.

## Decisions (owner, 2026-11-07)

- **Extraction:** a background pass with a small model (Haiku 5.5) when a thread goes quiet.
  It reads the messages since the last pass and proposes to add, update or forget items. Its
  tokens count in the person's monthly allowance (ADR-031).
- **Control:** full. A Memory section on Profile lists every item with its kind and source
  thread. Each item can be edited or deleted. One switch turns memory off for that person
  (no extraction, no recall). Otto also forgets when asked.
- **Visibility:** owner only, scoped like conversations. An administrator using "view as"
  sees it as that person would (ADR-020). There is no team-wide memory screen.

## In Scope (must-haves)

- Memory items per person, each with a kind, a text (one fact, short), its source (thread and
  message, or "you told Otto", or "computed"), and created and updated times. The kinds are:
  personal preference, work context (role, team, customer, projects), ServiceNow focus
  (modules, tables, releases, instances), communication style, and other.
- Computed items: the person's most-used ServiceNow areas (tables, plugins and Otto actions
  touched), derived from telemetry and conversation tool calls. They are free, exact, and
  refreshed by the same pass. These items can be hidden, but not edited.
- The extraction pass:
  - It runs in the background after a thread has been quiet for a set time, and processes
    only new messages.
  - It returns structured operations (add, update, forget, each naming the item it changes).
  - It is capped per run and skipped when memory is off, when the allowance is exhausted, or
    when the conversation is simulated.
- Recall: at the start of a thread, the person's current memory is frozen into a block sent
  to Claude with the system prompt. The block stays byte-identical for the whole thread, so
  prompt caching holds (ADR-023). A new thread picks up changes.
- Otto tools: `remember` (add an item the person states), `forget` (delete by match, confirmed
  in words), and `my_memory` (list it).
- Profile > Memory: list, edit, delete, delete all, and the on/off switch. Phone layouts
  follow ADR-030.
- Telemetry: every extraction call is recorded as usage (ADR-028).

## Out of Scope (anti-creep fence)

- We will NOT share memory between people, groups or tenants, and will NOT give
  administrators a team memory view.
- We will NOT store secrets: the extraction prompt refuses credentials, keys, passwords and
  personal identifiers, and a filter drops anything that looks like one.
- We will NOT do embeddings, vector search or semantic retrieval. The memory is small enough
  to send whole, with a hard cap on items and characters.
- We will NOT extract from attachments' contents, only from the conversation text.
- We will NOT use an external memory service; everything stays in the workbench database.
- We will NOT let memory change Otto's permissions or tool access.

## Acceptance Criteria

- [ ] A person's memory is invisible to every other person, including administrators outside
  "view as" (tests on the repository and the API).
- [ ] After a quiet thread, the pass adds an item stated in it ("I work for Acme on ITSM"),
  updates a changed one, and records its usage against the allowance. Tests use a fake
  Claude client, never the real API.
- [ ] With memory off, no pass runs and no memory is sent to Claude.
- [ ] A new thread's first request carries the memory block, and the block is identical on
  every later request of that thread.
- [ ] `remember`, `forget` and `my_memory` work from the conversation; `forget` confirms first.
- [ ] Profile > Memory edits and deletes items, and the switch works (Playwright).
- [ ] An item that looks like a secret is never stored (test with planted keys).
- [ ] The computed "most used ServiceNow areas" items reflect telemetry (test).

## Success Metrics

- Testers stop restating their role and focus in new threads; spot-check transcripts.
- Extraction costs well under 5% of a person's monthly allowance.
- No secret ever appears in a memory item.

## Dependencies

- ADR-002 (Otto on the Claude API), ADR-020 (impersonation), ADR-023 (prompt caching and
  budgets), ADR-028 (telemetry), ADR-031 (allowances).
- EPIC-018 story 01 (the feedback row) adds schema v15; memory takes the next version.
- An ADR (ADR-034) records the storage, the extraction trigger and the caching layout.

## Out of Library Scope (always)

- The Claude API (Anthropic) runs the model. The workbench owns storage, scheduling, policy
  and the UI.

## Resolved Questions (owner, 2026-11-07)

- Quiet period before extraction: 10 minutes after the last message, adjustable by an
  administrator in the conversation limits.
- Caps on what Otto receives: 50 items and 4,000 characters per person. Past the cap, the oldest
  least-used items are left out of recall first; they stay stored and visible on Profile.
