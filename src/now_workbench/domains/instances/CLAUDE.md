# instances domain context (Claude-only)

## What this domain does

The per-owner registry of ServiceNow instances: credentials sealed at rest, a connection
test that records status, and the platform profile (release, build, datacenter, nodes) read
from the live instance on a successful test (ADR-014). It also reads live record counts
through the Aggregate API for Otto's charts (ADR-028). It does NOT install plugins
(`plugins` depends on it, not the reverse), seed or roll back records (`seed`), parse
releases (`releases`, which it imports), or hold the workbench-wide fake-mode preference
(`settings`, read by the callers).

## Public entry points (all from `now_workbench.domains.instances`)

- `InstanceRepository` -- the registry: `list_instances`, `get_instance` (id or name),
  `get_default_instance`, `resolve` (id, or the default for None/""), `add_instance`,
  `update_instance`, `delete_instance`, `set_default_instance`, `update_instance_status`,
  `save_instance_profile`, `get_instance_profile`.
- `check_and_record_instance(conn, inst, timeout, fake_mode, transport)` ->
  `(status, message, http_code)`. THE "test this instance" entry point: verifies auth,
  stores the status, and on a real success refreshes the profile.
- `count_records(inst, tables, ...)` / `daily_created(inst, table, days, ...)` -- async
  Aggregate API counts, a few requests at a time.
- `seed_default_instance_if_empty(conn)` -- first-run seeding from settings.
- Models: `InstanceRecord` (decrypted credentials, backend only), `InstancePublic` (API
  view, `has_password` instead of the password; build it with `to_public`),
  `InstanceCreate`, `InstanceUpdate`, `InstanceProfile`, `InstanceNode`, `InstancePurpose`
  and `INSTANCE_PURPOSES` (demo, development, test, production).

## Wiring

- Tables: instances (owner-scoped by `owner_email`, credentials in `credentials_sealed`),
  instance_profiles and instance_nodes (keyed by instance id, cascade on delete), and
  instance_plugins (cascades too; written by `plugins`).
- Several repositories on one connection share its transaction.
- Imports from platform: `current_owner` / `owner_scope`, `seal_secret` / `unseal_secret`,
  `settings`. From other domains: `releases` (`UNKNOWN_RELEASE`, `BUILD_PROPERTY`,
  `parse_release_family`) and `identity` (`UserRepository` in bootstrap only).
- Imported by domains `seed`, `plugins`, `capture`, `runbooks`, `properties`,
  `synthesizer`, `demos` (mostly `InstanceRecord` as a parameter type), and by
  `interfaces/api/instances.py`, `replies.py`, `captures.py`, `properties.py`,
  `demo_support.py`, `app.py`, the CLI modules and the Otto tools (`base.py`,
  `instances.py`, `instance_charts.py`, `operations.py`, `show.py`, `system.py`).
- `interfaces/__init__.py` registers `seed_default_instance_if_empty` with `on_migrated`, so
  it runs right after a database file is created or migrated.

## Invariants and gotchas

- Owner scoping (ADR-018): every query through `list_instances`, `get_instance`,
  `get_default_instance`, `add_instance` and `set_default_instance` calls `current_owner`,
  which raises `NoOwnerError` outside an `owner_scope` (fail closed).
  `update_instance_status` and `get_instance_profile` filter by id only: pass an id you got
  from an owner-scoped read.
- Names are unique per owner and case-insensitive (`COLLATE NOCASE`); a clash raises
  `ValueError`, which the API maps to 409. Ids are one global namespace: `add_instance`
  with an id another owner holds silently mints a fresh `inst-` id instead.
- `add_instance` with an existing id of yours is an upsert (replace), not an error.
- One default per owner (partial unique index). `get_default_instance` promotes the first
  by name when none is set (it writes); `delete_instance` re-elects one.
- The release is never stored on the instance row: it is read from the profile
  (`UNKNOWN_RELEASE` until one exists). Changing the URL in `update_instance` deletes the
  stale profile and nodes.
- An empty password in `InstanceUpdate` keeps the stored one; credentials are always
  re-sealed with a per-instance GCM context (`instance:<id>`), never stored plain (ADR-012).
- Never return `InstanceRecord` from a route; use `to_public`.
- Simulated means: `fake_mode` passed, `settings.fake_mode`, or a URL starting `fake://` or
  `http://fake`. A simulated test fakes the outcome from the URL (`auth-failed`,
  `unreachable`) and never collects a profile. `count_records` / `daily_created` raise
  `ValueError` on a simulated instance rather than invent figures.
- A count the instance refuses is None, never 0 (ADR-028). `collect_instance_profile`
  returns None when nothing could be read, so an old profile is never wiped by an empty one.
- `seed_default_instance_if_empty` owns the seeded row as the first administrator, or "" (an
  orphan, claimed later by `claim_orphans`) when none exists yet.

## Do not reinvent

- Use `check_and_record_instance` for any connectivity test; do not call the Table API or
  write `status` yourself.
- Use `InstanceRepository.resolve` for "this id or the default". Otto's fuzzy lookup (id,
  name, or a unique URL fragment) is `resolve_instance` in `interfaces/ai/tools/base.py`.
- Live table counts: `count_records` / `daily_created`, not a new stats client.
- Fake detection lives in `is_simulated` (`connectivity.py`), which is not on the public
  root; other packages currently re-derive it (see Known gaps).

## Known gaps

- `is_simulated` is not exported. `interfaces/ai/tools/operations.py` (`_is_fake`) checks
  `ctx.fake_mode` and `fake://` but not `http://fake`, and the seed API trusts the request's
  `fake_mode` flag.
- Two first-run seeders exist: `seed_default_instance_if_empty` (id `primary-instance`)
  and `seed_database` in `interfaces/api/app.py` (id `default-instance`, at app startup,
  only when the operator has no instance yet).
