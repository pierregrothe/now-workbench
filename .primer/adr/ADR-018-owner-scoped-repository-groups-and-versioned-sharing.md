# ADR-018: Owner-scoped repository, groups and versioned sharing

**Status:** accepted
**Date:** 2026-11-06

## Context

PRD-003 makes every object per user and adds group sharing with approval and versions. About
150 call sites read instances, threads, seed runs and preferences through `db_session()`. Each
would need an owner argument, and one forgotten call would leak another person's credentials.
Demo bundles are directories on disk, not database rows.

## Decision

- **The owner is ambient and the repository fails closed.** `AccessMiddleware` puts the verified
  email in a `ContextVar` (`now_workbench.auth.owner`) for the lifetime of each HTTP request or
  WebSocket. FastAPI copies context into worker threads and tasks. Every owner-scoped repository
  query reads it; when it is unset the query raises instead of returning all rows. The CLI runs
  as the first administrator (or the local operator when there is none). Tests set it
  explicitly.
- **Schema v8.** It adds `owner_email` to `instances`, `chat_threads` and `seed_operations`.
  Instance names are unique per owner, and there is one default instance per owner (the
  `instances` table is rebuilt; migrations run with foreign keys off and then run
  `foreign_key_check`). Preferences become one row per user. Existing rows go to the earliest
  administrator. Rows created before any administrator exists are claimed by the first one
  at setup.
- **Groups.** `groups` is (name, kind in region/territory/business_unit). `group_members` holds
  (role member/admin, status pending/active).
- **Artifacts.** `artifacts` maps a bundle id to its owner. `artifact_versions` records each
  snapshot. A snapshot is a zip under `<data>/artifact-versions/<id>/v<n>.zip`, and is
  extracted read-only to `<data>/published/<id>/v<n>/` on first use. `artifact_shares` is
  (target group or global, version, status pending/approved/rejected/superseded). Approving
  a version supersedes the older approved share for the same target.
- **One resolver for bundle access.** `sharing.access.resolve_bundle(repo, id, write)` returns
  the owner's working directory, or for a recipient the snapshot of the newest version
  approved for them. Writes are owner-only. Anyone else gets 404, so the existence of another
  person's bundle is not revealed. Bundles found on disk without an owner are registered to
  the first administrator, with v1.

## Consequences

- An owner-scoped query cannot be forgotten: a missing owner is an error, not a leak.
- Bundle ids remain one namespace on disk, so cloning to an id another person uses fails
  with "already exists".
- Snapshots copy captured media, so versions of capture-heavy bundles use disk space.
- Administrators can no longer see or manage other people's instances. The Team screen remains
  their tool for access.
