# ADR-028: Telemetry, Live Instance Charts and Rendered Text

**Status:** accepted 2026-11-07
**Date:** 2026-11-07
**Builds on:** ADR-013 (no fabricated data), ADR-020 (impersonation), ADR-023 (token budgets),
ADR-026 (Actions screen), ADR-027 (chart tiles)

## Context

The owner asked (2026-11-07) whether telemetry was enabled and enforced so every KPI can be
charted, asked to close what ADR-027 left uncovered (tokens per day, live instance figures),
and noticed Otto's text showed raw markdown. Measured state: nothing was recorded
systematically. Otto's token use was summed into one weighted total per conversation (the
input, output and cache split was discarded), and no action run was recorded at all.

Owner decisions: keep charts in plain SVG (no chart library); everyone charts their own usage
and administrators also chart the team, per person.

## Decision

### 1. Telemetry recorded where everything passes

A `telemetry` domain owns two tables (schema v13): `usage_events` (one per Claude call:
model, input, output, cache write and cache read tokens, conversation) and `action_events`
(one per action run: name, source `otto` or `actions`, outcome `ok`, `failed` or `pending`,
duration). Each row carries `owner_email` (whose data it is) and `actor_email` (who really
acted, so "view as" stays attributable).

- **Actions:** `execute_tool` records every run, by Otto or on the Actions screen, after it
  finishes. A failed telemetry write is logged as an error and never undoes or hides the
  action.
- **Claude calls:** `_AgentLoop.absorb` records each response's usage; both agent drivers
  (async and sync) pass through it. The legacy streaming path (`OttoClient.stream_chat`)
  reports its final message through an `on_usage` callback that records it.

### 2. Enforced, not only wired

Two architecture tests fail the build if code bypasses the recorders:

- only `tools/base.py` may call a tool's `spec.handler(`;
- Messages API calls may appear only in `agent.py` (each wrapped by `loop.absorb(`) and in
  `client.py` (the recorded stream, and the one-token API-key check, which answers nobody).

They run in the pre-push gate (policy `telemetry-recording`).

### 3. Charts that read it

- `usage_history` adds tokens per day, stacked by kind.
- `action_history`: runs per day by outcome, and the eight most used actions with
  failures and mean duration.
- `team_usage` (administrators only; the service refuses anyone else): team tokens per day,
  tokens by person, actions by person.
- `instance_record_counts` and `instance_records_over_time`: live, read-only counts from the
  ServiceNow Aggregate API (`/api/now/stats`), six requests at a time. A count the instance
  refuses is reported by name and never drawn as zero; a refused day means no chart rather
  than a gap filled in. A simulated instance or workbench refuses: there are no live figures
  to show. Table names are checked before they go into the URL path. Days are as the
  instance user's time zone sees them.

### 4. Otto's text renders as HTML

`<now-markdown>` turns a safe subset (paragraphs, line breaks, headings, lists, fenced code,
bold, italics, inline code, http(s) and mailto links) into Lit templates. Raw HTML from the
model is never injected, so markup or script in a reply, a tool result or a record shows as
text. Prompting alone was not used: Claude's natural output is markdown, and asking it for
HTML would let any injected content reach the page. The system prompt now allows light
formatting; the reply stays one or two sentences.

### 5. Mutation testing of the new code

The new modules (chart helpers, history and instance chart tools, telemetry, instance stats)
were mutation-tested with mutmut 3.8 (fork-server isolation; plain fork crashes on macOS
under Python 3.14): 966 of 966 mutants killed. Code that produced equivalent mutants (SQL
keyword case, `sqlite3.Row` key case, a slice that could never cut, `zip(strict=True)` over
equal lengths, a URL slash httpx already normalises) was restructured rather than excluded.
Mutation testing is not yet a standing gate; it is run on demand.

## Consequences

- Otto has 76 tools; every run and every Claude call is recorded per person.
- Telemetry rows accumulate without a retention limit; a purge policy can come with the
  scheduled backups.
- Tokens before this change exist only as per-conversation totals; per-day history starts now.
