# sharing domain context (Claude-only)

## What this domain does

Decides who may read or change a demo bundle, freezes bundles into immutable numbered
versions, and runs the share-and-approve flow (ADR-018, PRD-003). The owner works on the live
directory under the bundles dir; a recipient of an approved share reads an extracted, frozen
snapshot of the newest version approved for them; anyone else gets "not found". It also holds
the group-management service rules (create, join, members), layered over the groups domain.
It does NOT create, validate, clone or delete bundle directories (`BundleManager` in the
bundles domain), store groups or memberships (`GroupRepository` in the groups domain), or
decide roles (identity).

## Public entry points (all from `now_workbench.domains.sharing`)

Access (`access.py`, reads the ambient owner):
- `resolve_bundle` (conn, artifact_id, write=False) -> `BundleAccess`; raises `LookupError`
  (not yours, not shared, or unknown) or `ReadOnlyBundleError` (shared, but `write=True`).
- `list_accessible` (conn) -> own bundles, then bundles shared with you.
- `BundleAccess`: frozen dataclass; `root` is a bundles directory containing `artifact_id`,
  `path` is the bundle itself, `kind` is owner or shared, `version`, `owner`.
- `register_new_bundle` (conn, artifact_id, owner): record ownership and save version 1.
- `save_version` (conn, artifact_id, note, created_by): snapshot the live directory as the next
  version (no permission check; the service wrapper checks).
- `sync_registry` (conn, operator) -> count: give unregistered bundles on disk to `operator`.

Service (`service.py`, every call takes `conn` and an `AuthUser` actor; shared by the API and
Otto, ADR-025):
- Groups: `list_groups`, `create_group`, `delete_group` (admins), `join_group`,
  `list_group_members`, `put_group_member`, `remove_group_member`.
- Versions and shares (owner only): `list_versions`, `save_new_version`, `list_shares`,
  `request_share`, `withdraw_share`.
- Approvals: `approval_inbox` -> `ApprovalInbox` (shares, join requests, group names),
  `decide_share`.

Models and storage: `ArtifactVersion`, `ArtifactShare`, `ShareTarget` (group or global),
`ShareStatus` (pending, approved, rejected, superseded), `ArtifactRepository`,
`delete_artifact_files` (artifact_id): remove every snapshot and published copy.

## Wiring

- `ArtifactRepository` (subclass of the platform `Repository`) owns the tables artifacts,
  artifact_versions and artifact_shares (schema v8 in `platform/db/schema.py`; versions and
  shares cascade on delete of the artifact, group shares cascade on delete of the group).
- On disk (`store.py`, under the data dir): artifact-versions/<id>/v<n>.zip is the frozen
  bundle; published/<id>/v<n>/<id>/ is the extracted read copy. The extra id level makes
  `published_root` usable as a bundles root, so engines taking (bundles_dir, bundle_id) work on a
  snapshot unchanged. Extraction is lazy, on first read.
- Imports: `GroupRepository` and its models from the groups domain; `AuthUser`,
  `UserRepository`, `is_admin`, `require_admin`, `normalize_email` from identity; platform
  `current_owner`, `LOCAL_EMAIL`, `safe_child`, `settings`, and the `DomainError` family.
- Callers: `interfaces/api/sharing.py` and `interfaces/ai/tools/sharing.py` (thin, over the
  service); `interfaces/api/demo_support.py` (`require_bundle` maps `LookupError` to 404 and
  `ReadOnlyBundleError` to 403); `interfaces/api/demos.py` and `interfaces/ai/tools/bundles.py`
  (register, list, delete); `interfaces/api/replies.py` (`list_accessible`);
  `interfaces/api/app.py` (`sync_registry` at start-up, `resolve_bundle` for the build and
  deploy routes); `interfaces/cli/main.py` (`sync_registry` after a command).
- Contracts: `acyclic-domains` -- sharing depends on groups and identity, so neither may
  import sharing.

## Invariants and gotchas

- Owner scoping is ambient: `resolve_bundle` and `list_accessible` call `current_owner`,
  which raises `NoOwnerError` outside an `owner_scope` (fail closed). The service functions
  instead use the `actor` argument's email.
- Never reveal existence: a bundle that is neither yours nor shared with you is `LookupError`
  in access (404); the service's `_require_owner` raises `NotFoundError` for any bundle you do
  not own. Only a bundle shared with you answers a write with `ReadOnlyBundleError` (403).
- Local mode only (no Access audience): every resolve and list first runs `sync_registry`
  for `LOCAL_EMAIL`. Behind Access this never runs per request, so a bundle created by a route
  must be registered explicitly with `register_new_bundle` or it is invisible to everyone.
- Owner access also needs the live directory: an owned id whose directory is gone falls
  through to the share path and ends in `LookupError`.
- Who decides: workbench admins create and delete groups, appoint group admins, and decide
  any share, global included. Group admins accept join requests and decide shares to their
  group. `request_share` auto-approves when the requester could approve it themselves, and only
  admins may share to a group they are not an active member of.
- A share always targets the newest saved version; `ConflictError` before any version exists.
  A new request supersedes the older pending one for the same target; approving supersedes the
  older approved one. `shared_with` returns the max approved version and excludes your own.
- `save_version` never overwrites: `snapshot_bundle` raises `FileExistsError` if that zip
  exists. Symlinks are skipped when zipping; archives are written to a .partial file and
  renamed.
- Deleting a bundle is three steps the caller does: `BundleManager` removes the directory,
  `forget_artifact` drops the rows, `delete_artifact_files` drops the snapshots.
- Errors: the service raises the platform `DomainError` family (mapped to HTTP in
  `interfaces/api/errors.py`); access raises built-ins (`LookupError`, `PermissionError`
  subclass), which each caller maps itself.

## Do not reinvent

"Is this bundle theirs or shared with them?" (`resolve_bundle`), "every bundle this person
can see" (`list_accessible`), freezing a directory into a versioned zip (`save_version`;
`snapshot_bundle` in `store.py` is internal), a read-only bundles root for a past version
(`resolve_bundle(...).root`; `published_root` is internal), or role checks on group and
share actions (the service functions; use them from new routes and Otto tools alike).
