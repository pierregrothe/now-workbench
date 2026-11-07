# ADR-031: Monthly Claude Usage Allowances

**Status:** accepted 2026-11-07
**Date:** 2026-11-07
**Builds on:** ADR-020 (impersonation), ADR-023 (token budgets), ADR-028 (telemetry)
**Story:** `.primer/epics/2026.11a-tester-safeguards/01-usage-caps-enforced.story.md`

## Context

Outside testers use the owner's Claude key and nothing limited what a person could spend.
The per-conversation budget (ADR-023) does not stop someone from starting new conversations.
Telemetry (ADR-028) now records every Claude call per person.

Owner decisions (2026-11-07): a monthly allowance, administrators exempt.

## Decision

- **Measure:** billable tokens this UTC month, counted from `usage_events` the way the
  conversation budget counts them: input + output + 1.25 x cache writes + 0.1 x cache reads.
  The weights now live in the telemetry domain, and the conversation budget imports them.
- **Allowance:** `monthly_allowance_tokens` in the conversation limits (default 10,000,000,
  at least 100,000). Per-person overrides and the settings screen are story 02.
- **Rule:** below 80% nothing is said; from 80% the answer carries a warning (percentage,
  tokens, reset date); at 100% no Claude call is made. The HTTP API answers 429, and the
  WebSocket sends an error. Administrators are exempt. Under "view as" the person viewed is
  checked, as they would be.
- **Where:** `interfaces/api/allowance.enforce_allowance` runs beside the per-conversation
  check at every place a new question reaches Claude: thread messages, and the Otto
  WebSocket including its legacy stream (moved to `interfaces/api/otto_ws.py`). Nobody
  signed in means an error, never a skipped check. An architecture test fails if a route
  that checks conversation limits does not also check the allowance.
- **Warning transport:** an `X-Usage-Warning` header (the `usage_warning` event on the
  WebSocket), shown next to the prompt. It is never written into the conversation, so
  Claude never sees it and the history stays cacheable.

## Consequences

- Testers stop at their allowance until the 1st of next month (UTC) or until an
  administrator raises it.
- Confirming an action Otto already proposed is not a new question and is not checked; the
  conversation budget follows the same rule.
