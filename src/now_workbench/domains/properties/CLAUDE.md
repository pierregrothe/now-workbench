# properties domain context (Claude-only)

## What this domain does

Applies a demo bundle's ServiceNow system properties (sys_properties) to an instance through
the Table API (reading each property's previous value just before changing it, and saving them
as a snapshot once the loop finishes), and restores those values on teardown (ADR-007). It also
reads live property values without changing them. It does NOT find or authorize the bundle
(`sharing` resolves it, `bundles` parses it), choose the target instance (`instances`), seed
records (`seed`), or orchestrate the full demo run (`demos`).

## Public entry points (all from `now_workbench.domains.properties`)

- `PropertyEngine` -- the only behaviour. `PropertyEngine(snapshots_dir=None)` defaults to
  `settings.get_data_dir()` / `snapshots` / `properties` and creates it.
  - `read_bundle_properties(bundle_path)` -> name -> value dict (empty on a missing or
    unparsable file).
  - async `apply_bundle_properties(bundle_id, bundle_path, instance, client=None,
    fake_mode=False)` -> `PropertyApplyResult`.
  - async `restore_properties(bundle_id, instance, client=None, fake_mode=False)` ->
    `PropertyApplyResult`; deletes the snapshot afterwards.
  - async `read_live_values(names, instance, client=None)` -> name -> value or None.
  - `load_snapshot`, `save_snapshot`, `delete_snapshot` (keyed by bundle id and instance id).
- Models: `PropertySnapshot` (`original_values`: name -> previous value, None when the
  lookup found no record, including a non-200 reply), `PropertyApplyResult` (`success`,
  `applied_count`, `restored_count`, `details`), `PropertyRecord` (exported, unused in src).

## Wiring

- No repository and no tables: snapshots are JSON files named
  `<bundle_id>_<instance_id>.json` (slashes replaced) in the snapshots directory.
- `instance` is an `InstanceRecord` from `instances` (decrypted credentials). Callers get it
  inside `with db_session() as conn:` via `InstanceRepository` (`resolve`, or the API's
  `target_instance` helper in `interfaces/api/demo_support.py`). The REST, reset and CLI callers
  call the engine after the session closes; the demos pipeline and Otto's tools call it while
  their connection stays open.
- Imported by `domains/demos/pipeline.py` (`configure_properties`, and `read_live_values` for
  the vendor prefix property before Fluent project generation), `interfaces/api/properties.py`,
  `interfaces/api/demos.py` (reset), `interfaces/cli/properties.py`,
  `interfaces/ai/tools/operations.py`.
- It imports `instances` (`InstanceRecord`) and `settings` from platform, plus httpx.
- Contracts: `acyclic-domains` -- `instances` must not import this domain; `demos` imports it.

## Invariants and gotchas

- Bundle file: `properties/sys_properties.json`, else `sys_properties.json` at the bundle
  root. Values are coerced to strings. `BundleManager.inspect_bundle` only reads the first
  location, so a root-level file applies but does not show in bundle info.
- Fake mode is `is_simulated(instance, fake_mode)` (instances domain): no
  HTTP, a simulated snapshot of `old_<name>` values is saved, and restore just deletes it.
- Auth: basic auth only when `auth_type` is `basic`; any other type sends no credentials.
- Fail-soft: apply and restore never raise for HTTP trouble; they return
  `success=False` with the error in `details`. Apply reports per-property failures in
  `details` and `success=False`; restore drops a failed update silently and still reports
  success and deletes the snapshot.
- The snapshot is written once, after the whole apply loop. An exception mid-loop leaves the
  properties already changed with no snapshot to restore from.
- Applying twice without a restore overwrites the snapshot with the already-applied values,
  losing the true originals.
- Restore skips properties whose original value was None: a property the apply created is
  left on the instance, not deleted.
- A passed `client` is used as `async with client`, so the engine closes it on exit; do not
  reuse it afterwards.
- Property names go into `sysparm_query` unencoded.
- `read_live_values` has no fake mode; callers skip it for simulated instances.
- Snapshots are not owner-scoped: they are keyed only by bundle and instance id.

## Do not reinvent

- Reading a sys_properties value from an instance (`read_live_values`).
- Snapshot-before-change and restore of demo properties; teardown flows already pair this
  with seed rollback (`interfaces/api/demos.py`, `interfaces/cli/properties.py`).
- Other Table API clients live in `seed`, `plugins`, `runbooks` and `instances`; reuse those
  patterns rather than adding a new HTTP helper.
