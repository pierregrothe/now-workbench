# groups domain context (Claude-only)

## What this domain does

Stores the organisation's groups (a region, territory or business unit) and their members:
join requests, acceptance, and a per-group role of member or admin (PRD-003, ADR-018). It
is pure persistence over two tables plus the queries other rules need ("which groups is X
an active member of", "does Y administer group G"). It does NOT decide who may create,
delete or manage a group: those rules live in the `sharing` service (`create_group`,
`put_group_member`, ...). It does NOT share artifacts (`sharing`) or decide who may "view
as" whom (`may_impersonate` in `identity`); both read it.

## Public entry points (all from `now_workbench.domains.groups`)

- `GroupRepository`:
  - groups: `create_group(name, kind, description, created_by)`, `get_group(group_id,
    viewer)`, `list_groups(viewer)` (every group, by kind then name), `delete_group`;
  - membership: `request_to_join`, `put_group_member(group_id, email, role, decided_by)`,
    `remove_group_member`, `list_group_members` (pending first), `pending_join_requests`
    (None means all groups; an empty list returns nothing);
  - lookups: `is_group_admin`, `active_group_ids`, `administered_group_ids`.
- Models: `Group` (with the viewer's `my_status` / `my_role` and the active
  `member_count`), `GroupMember`, and the enums `GroupKind` (region, territory,
  business_unit), `MemberRole` (member, admin), `MemberStatus` (pending, active).

## Wiring

- Tables: groups (name unique, case-insensitive) and group_members (primary key group id +
  email; cascade on group delete). Shares with a group (artifact_shares, owned by
  `sharing`) also cascade when the group is deleted.
- The domain imports nothing but its own models and platform.
- Imported by `sharing` (`service.py` for the group rules and approvals, `access.py` for
  "shared with my groups"), `identity` (`impersonation.py`: group admins may act as their
  groups' members), and the interfaces `interfaces/ai/audience.py` (Otto's groups line),
  `interfaces/ai/tools/sharing.py` and `interfaces/api/sharing.py` (types only; they call
  the `sharing` service).
- Contracts: `acyclic-domains` -- `identity` and `sharing` depend on `groups`, so `groups`
  must never import either.

## Invariants and gotchas

- Groups are SHARED, not owner-scoped: no query calls `current_owner`. Every method takes
  the email it is about explicitly (`viewer`, `email`, `created_by`, `decided_by`).
- The repository enforces no permission at all. Go through the `sharing` service
  (`create_group`, `delete_group`, `join_group`, `list_group_members`, `put_group_member`,
  `remove_group_member`), which applies the rules: workbench administrators create and
  delete groups and alone appoint group admins; a group admin (or a workbench admin)
  lists members and accepts requests; anyone may leave or ask to join.
- Only ACTIVE rows count: `is_group_admin`, `active_group_ids`,
  `administered_group_ids` and `member_count` ignore pending requests.
- `request_to_join` never changes an existing membership (`DO NOTHING`); `put_group_member`
  upserts and sets the row active with the given role, so it also changes the role of an
  existing member.
- `create_group` raises `ValueError` on a duplicate name; the `sharing` service maps it to
  `ConflictError`. Ids are `grp-` + 8 hex.
- Emails are compared as stored: normalise before calling (the service uses
  `normalize_email` for adds).
- Membership drives other rules: dropping someone from a group can end an impersonation
  (`effective_user` revokes one that `may_impersonate` no longer allows) and hides
  group-shared bundles from them.

## Do not reinvent

- "Groups of this person" / "groups this person administers": `active_group_ids`,
  `administered_group_ids`; "pending requests I can decide": `pending_join_requests` with
  the administered ids (see `approval_inbox` in `sharing`).
- Permission checks on groups: `sharing` service functions, not new checks around the
  repository.
