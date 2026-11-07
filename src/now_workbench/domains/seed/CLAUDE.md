# seed domain context (Claude-only)

## What this domain does

Loads a demo bundle's seed records into a ServiceNow instance over the Table API, keeps an
owner-scoped audit row per run listing every record it created (table + sys_id), and uses
that list to verify the records still exist or to roll them back. Relative dates in seed
files (`{{NOW}}`, `{{TODAY - 2h}}`, `{{TODAY + 3d}}`) are resolved at load time. It does NOT
find or validate bundles (`bundles`, and `require_bundle` / `bundle_path` in the
interfaces), deploy the Fluent app that may rename tables (`demos` passes the `table_map`),
restore system properties (`properties`), or own the instance registry (`instances`).

## Public entry points (all from `now_workbench.domains.seed`)

- `SeedEngine` -- built per call with `SeedEngine(conn, fake_mode=..., transport=...)`:
  - async `load_and_seed(bundle_id, bundle_path, instance_id=None, table_map=None)` ->
    `SeedOperationRecord`;
  - async `verify(operation_id)` -> list of `(SeedRecordItem, exists, detail)`, read-only
    (`SeedRecordItem` is not on the public root);
  - async `rollback(operation_id)` -> `(deleted_count, errors)`.
- `SeedRepository` -- `record_seed_operation`, `get_seed_operation`,
  `list_seed_operations(limit=50)` (newest first), `update_seed_operation_status`,
  `daily_status_counts(since)` for the history chart.
- `SeedOperationRecord` -- id (`seed-` + 8 hex), bundle and instance ids, status,
  `created_records`, `created_at`, `error`.

## Wiring

- Table: seed_operations, owner-scoped by `owner_email`, `created_records` as JSON. It has
  deliberately NO foreign key to instances, so history outlives a removed instance.
- `SeedEngine` opens `InstanceRepository` and `SeedRepository` on the connection it is given
  (from `db_session()`, or the caller's unit of work); both share its transaction.
- Imports `InstanceRecord`, `InstanceRepository` from `instances`; `current_owner` from
  platform. No other domain import.
- Callers: `demos` (`pipeline.py`: seeds after the optional Fluent deploy, passing its
  `table_map`, ADR-022), `interfaces/api/demos.py` (seed, rollback, list, reset),
  `interfaces/cli/bundles.py` and `interfaces/cli/properties.py`, and the Otto tools
  `interfaces/ai/tools/operations.py`, `show.py`, `history.py`.

## Invariants and gotchas

- Every repository query calls `current_owner`: no owner scope means `NoOwnerError`, and
  another owner's operation reads as "not found" (`ValueError` from the engine).
- Seed files: `<bundle>/seed/*.json`, read in file-name order; each file is a JSON LIST of
  `{"table": ..., "fields": {...}}` (`data` is accepted for `fields`; `table` defaults to
  incident). A non-list file is skipped silently; an unreadable one raises
  `SeedPayloadError` (a `ValueError`, not on the public root). No records at all raises
  `ValueError`.
- `load_and_seed` is not atomic on the instance: it posts one record at a time and stops at
  the first failure. After any failure while posting, it still writes the audit row first
  (status failed, `error` truncated to 500 chars) and then raises `RuntimeError` naming the
  operation id to roll back; an unknown instance or no seed records raise `ValueError` before
  any row exists.
- `rollback` deletes in reverse creation order; a 404 counts as deleted. Any error leaves
  status `rollback_failed` (retry-able); only a clean pass sets `rolled_back`, and a second
  rollback of that raises `ValueError`.
- `rollback` (and a non-fake `verify`) resolves the instance by the stored id through the
  owner-scoped registry: if the instance was deleted it raises `ValueError` even though the
  audit row remains.
- `fake_mode` is decided by the CALLER and only by it: the engine never looks at
  `settings`, the `sdk_fake_mode` preference or a `fake://` URL. Callers decide through
  `is_simulated` (instances); the seed and rollback APIs OR the request flag with
  `sdk_fake_mode` and the target instance, so a simulated instance is never posted to. Fake
  posts return `fake_sys_...` ids, fake deletes succeed, fake `verify` reports "simulated".
  Seeding and rollback still need a registered instance in fake mode.
- Date wizard: `{{TODAY}}` and `{{NOW}}` both mean the current UTC instant (TODAY is not
  midnight); units s, m, h, d, w; output `YYYY-MM-DD HH:MM:SS`, case-insensitive.
- Non-basic auth sends no credentials (`httpx.USE_CLIENT_DEFAULT`).

## Do not reinvent

- Relative-date substitution in any dataset: `transform_dataset_dates` /
  `resolve_date_expression` in `date_wizard.py` (same-domain only; not exported).
- Rollback handles: always record through `record_seed_operation`; never post records to an
  instance without an audit row.
- "Roll back this bundle's live seed runs on one instance" is filtered by hand from
  `list_seed_operations(limit=100)` in three places (`reset_demo` in
  `interfaces/api/demos.py`, `_reset` in `operations.py`, and `interfaces/cli/properties.py`);
  reuse one of those shapes or lift it here rather than writing a fourth.
