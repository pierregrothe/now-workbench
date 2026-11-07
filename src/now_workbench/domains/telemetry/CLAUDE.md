# telemetry domain context (Claude-only)

## What this domain does

Records every Claude call Otto makes (tokens by kind) and every action (tool) run, by Otto or
by hand, at their single choke points (ADR-028); aggregates them per day, action and person
for the history charts; purges them past the retention window (ADR-029); and computes the
monthly per-person Claude allowance with administrator overrides (ADR-031). It does NOT call
Claude or run tools (`interfaces/ai`), enforce the allowance at the HTTP edge
(`enforce_allowance` in `interfaces/api/allowance.py`), schedule the purge
(`interfaces/api/retention.py`), or own the default allowance (the conversation limits in
`conversations`).

## Public entry points (all from `now_workbench.domains.telemetry`)

- Writers: `record_usage(conn, actor, model, counts, thread_id)` (counts keyed input,
  output, cache_write, cache_read) and `record_action(conn, actor, name, source, outcome,
  duration_ms)`. Both stamp `owner_email` from `current_owner` and `actor_email` from the
  real person behind a "view as".
- Team view: `team_by_person(conn, actor, since)` -> (tokens by person, runs by person).
- Retention: `purge_expired(conn, retention_days, now)` -> events deleted.
- Allowance: `check_allowance(conn, user, default, now)` -> `Allowance`;
  `team_allowances(conn, actor, default, now)` -> list of `PersonAllowance`;
  `set_allowance_override(conn, actor, email, tokens)` (None returns to the default);
  `allowance_for(conn, email, default)`.
- `TelemetryRepository` -- raw reads for charts: `daily_tokens` (`everyone=True` for the
  team), `daily_actions`, `action_totals`, `billable_since`, plus the by-person and override
  reads.
- Models and constants: `UsageEvent`, `ActionEvent`, `ActionSource` (otto, actions),
  `ActionOutcome` (ok, failed, pending), `TOKEN_KINDS`, `CACHE_READ_WEIGHT` (0.1),
  `CACHE_WRITE_WEIGHT` (1.25), `WARN_AT_PERCENT` (80), `MIN_ALLOWANCE`, `MAX_ALLOWANCE`.

## Wiring

- Tables: usage_events and action_events (both carry owner and actor emails, no foreign
  keys) and usage_allowances (one override per email).
- The service functions take the connection and build the repository themselves.
- Imports `AuthUser`, `Role`, `is_admin`, `require_admin`, `list_team` from `identity`;
  `current_owner` and `InvalidInputError` / `NotFoundError` from platform.
- Call sites: `record_usage` in `interfaces/ai/agent.py` (`_AgentLoop.absorb` for every
  Messages API response, and `stream_usage_recorder` for streams outside the loop);
  `record_action` in `execute_tool` (`interfaces/ai/tools/base.py`), which logs and swallows
  a `sqlite3.Error` so a lost record never undoes the action; `check_allowance` in
  `enforce_allowance` and `interfaces/api/usage.py`; `team_allowances` and
  `set_allowance_override` in `usage.py` and `interfaces/ai/tools/admin.py`;
  `team_by_person` and `TelemetryRepository` in `interfaces/ai/tools/history.py`;
  `purge_expired` in `purge_telemetry` (at startup, then daily, with
  `settings.telemetry_retention_days`). `CACHE_READ_WEIGHT` / `CACHE_WRITE_WEIGHT` are also
  read by `interfaces/ai/conversation.py`.

## Invariants and gotchas

- Reads are owner-scoped unless they say otherwise: the `_own` path adds the owner filter
  through `current_owner` (raises outside a scope); the by-person reads and
  `daily_tokens(everyone=True)` see everyone, so only call them after an admin check.
  `team_by_person`, `team_allowances` (through `list_team`) and `set_allowance_override`
  call `require_admin` and raise `ForbiddenError`.
- `owner_email` is whose data it is (the viewed person under "view as"); `actor_email` is
  who really acted. Passing `actor=None` records the owner as the actor (outside a request).
- Billable tokens = input + output + 1.25 x cache writes + 0.1 x cache reads, the same
  weighting the conversation budget uses (ADR-023). `tokens_by_person` and `daily_tokens`
  are raw sums, not billable; only `billable_since` / `billable_by_person` weight.
- `check_allowance` counts `billable_since` for the CURRENT OWNER but looks up the override
  for `user.email`: call it with the owner scope set to that user. Administrators are always
  `exempt` (by their effective roles, so under "view as" the viewed person is judged).
- Allowance months are UTC calendar months; `resets_on` is the next month's first day.
  States: ok, warn (80% or more), refused (100% or more), exempt.
- Overrides must lie in 100,000 to 1,000,000,000 (also a CHECK in the table) and the email
  must be on the team, else `InvalidInputError` / `NotFoundError`.
- `purge_expired` deletes everyone's events older than the window, in one transaction.
- Timestamps compare as text: `since` is a YYYY-MM-DD day or an ISO `...Z` instant.

## Do not reinvent

- Any new path that calls Claude or runs a tool must go through the existing choke points
  (`_AgentLoop`, `stream_usage_recorder`, `execute_tool`); do not add a second writer.
- The allowance gate is `enforce_allowance`; do not re-check `Allowance.state` by hand.
- Billable weighting: `CACHE_READ_WEIGHT` / `CACHE_WRITE_WEIGHT`, never new literals.
