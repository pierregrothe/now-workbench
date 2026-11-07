# Review record -- feature/chat-feedback-row

- Head: f7a464991f1d3cd66cb0a94e5cecdcdedfcb9fe2
- Branch: `feature/chat-feedback-row`
- Date: 2026-11-07
- Scope: EPIC-018 story 01. Thumbs up/down, an optional comment and Get help under Otto's replies.
  - Schema v15 adds `message_feedback`: one row per reply, scoped through its thread, cascaded with the message.
  - `PUT` and `GET /api/feedback`. Admins see all ratings and consultants their own; lists are capped at 200.
  - A "Reply feedback" Settings section. The thread message API now accepts role `user` only.
- Process: top-tier implementer; one Sonnet adversarial review and two verify rounds.
  - Round 1: 1 MAJOR. A comment was lost when someone changed their rating after a reload, and the tests asserted the loss.
    - MINOR findings: a denormalised owner went stale after `claim_orphans`; assistant replies could be forged through the API; the list was unbounded; accessibility (focus loss, unnamed buttons, a green pressed thumbs-down, the comment box opening before the save); missing tests for impersonation, the consultant UI and failures.
  - Round 2 (7602372) fixed everything. History carries `{rating, comment}`, and a null comment keeps the stored one. v15 has no owner column. Roles are `Literal["user"]`, and the other fixes are as listed.
  - Verify: no BLOCKING or MAJOR. MINOR: an unsent draft was overwritten when the history reloaded.
  - Round 3 (942fe4e) fixed it, red first.

## Verified

- 1,208 pytest at 100% coverage and 107 Playwright tests pass.
- A v14 database upgrades to v15, idempotently.
- The impersonation, ownership and cascade behaviour was reproduced by the reviewer.
- Otto's own replies are stored through `ChatMessageRecord` and are unaffected by the role restriction.

## Not done (follow-ups)

- v15 was edited in place before release. A developer database that ran the first commit must be deleted; none in use did.
- There is no way to withdraw a rating (no DELETE).
