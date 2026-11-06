# ADR-020: Impersonation ("View as someone")

**Status:** accepted
**Date:** 2026-11-06

## Context

The owner asked that administrators can act as someone else: "A global admin can impersonate
anyone, a group admin can impersonate anyone from his group." With everything per user
(ADR-018), this is the only way to see exactly what a tester sees or to fix their setup.

## Decision

- **Server-side, per signed-in person.** `impersonations` (schema v9) holds at most one target
  per real email. After Cloudflare Access verifies the real person, the access middleware
  swaps in the target as the effective user: their email becomes the ambient owner (ADR-018)
  and their roles apply. Every workload (instances, conversations, Otto and its tools, bundles,
  sharing, approvals, settings) therefore runs as the target with no per-route code. The UI
  sends no header and keeps no client state that could be forged.
- **Rules, judged on the real person and re-checked on every request.**
  - An administrator may act as any member.
  - A group administrator may act as accepted members of a group they administer, but never as
    a workbench administrator, which would escalate their privileges.
  - Nobody acts as themselves or as someone without a role.
  - If the right disappears (demoted, removed from the group), the next request ends the
    impersonation and logs it as `revoked`.
- **Always escapable and audited.** `/api/impersonation` (status, start, stop) uses the real
  identity, so stopping works even when the target's roles are smaller. Starts, stops and
  revocations are appended to `impersonation_log` and written to the server log. A banner shows
  "Viewing as X (you are Y)" with a Stop button.

## Consequences

- Actions taken while impersonating are recorded as the target's (they own what is created).
  The impersonation log is the record of who was really acting at the time.
- Tests cover each workload under impersonation (`tests/test_impersonation.py`).
