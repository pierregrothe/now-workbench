# plugins domain context (Claude-only)

## What this domain does

Answers "are the plugins this demo bundle requires active on this instance?" and remembers
what it has seen active per instance. A real instance is asked read-only over the Table API
(v_plugin); a simulated instance answers from the recorded list. It does NOT install or
activate anything on a real instance: "install" only re-checks that the plugin is active and
records it, or records it outright when simulated. It does NOT read a bundle's
required_plugins (the demos pipeline reads the manifest through `BundleManager` and passes the
list in), decide overall demo readiness (`DemoPipelineEngine` in the demos domain combines
this with the releases check), or own instances and their credentials (instances domain).

## Public entry points (all from `now_workbench.domains.plugins`)

- `PluginManager` (conn, transport=None): `transport` is an optional httpx transport, the
  seam tests use to fake the instance.
  - `evaluate_plugins` (instance, required_plugins, fake_mode=False) ->
    `PluginEvaluationResult`.
  - `install_plugin` (instance, plugin_id, plugin_name=None, fake_mode=False) -> (ok, message).
  - `install_required_plugins` (instance, required_plugins, fake_mode=False) ->
    (records, messages): evaluate, then `install_plugin` each missing one.
- `PluginEvaluationResult`: required, installed, missing, `reasons` (plugin id -> why it is
  missing), `all_satisfied`.
- `PluginRecord`: one recorded plugin on one instance (status, installed_at).

`PluginRepository` is NOT exported; reach the table through `PluginManager` (its `plugins`
attribute).

## Wiring

- `PluginRepository` (`repository.py`) owns the instance_plugins table: primary key
  (instance_id, plugin_id), cascades on delete of the instance, upserted by
  `add_instance_plugin`. `PluginManager` opens it on the connection it is given; the demos
  pipeline passes its own connection.
- Imports `InstanceRecord` from the instances domain (url, username, password, auth_type,
  name, id) and the platform `Repository`. Uses httpx directly, not a platform client.
- Only caller in src: `DemoPipelineEngine` (`domains/demos/pipeline.py`) via
  `evaluate_bundle` and `install_required_modules`; the CLI, the API and Otto's demo tools
  reach plugins only through that engine.
- Contracts: `acyclic-domains` -- plugins depends on instances; demos depends on plugins.

## Invariants and gotchas

- Fail closed on the instance: any non-200, httpx error or unparseable JSON counts the plugin
  as missing (a 200 whose `result` is not a list of objects raises instead), with the reason
  recorded in `reasons`; it never claims a plugin is active on failure.
  A row counts as active when its active field reads "active" or "true".
- Simulated means `is_simulated(instance, fake_mode)` (instances domain); then no HTTP
  call is made and only the recorded rows count.
- Recording is one-way: a plugin seen active is upserted; nothing ever removes or deactivates
  a row. On real instances the live answer wins anyway; on simulated ones a recorded plugin stays
  "installed" forever.
- Owner scoping is inherited, not enforced: rows are keyed by instance id only, so the caller
  must have resolved the `InstanceRecord` through the owner-scoped instances repository.
- Basic auth is sent only when the instance's auth_type is "basic"; otherwise the request goes
  unauthenticated.
- Calls are synchronous httpx, one request per plugin, each with a 40 s timeout (unknown ids
  can take tens of seconds on the instance). Do not call from async code without moving it
  off the event loop. Every current path does: `run_full_pipeline` (`asyncio.to_thread`), the
  sync API evaluate route (threadpool), and Otto's tools on `/ws/otto` (`stream_run` runs
  tools via `asyncio.to_thread`), the thread reply worker and the sync actions route.
- `evaluate_plugins` strips ids and skips empty ones. `KNOWN_PLUGIN_NAMES` gives display names
  for four ids; unknown ids are recorded under the bare id by `evaluate_plugins` and as
  'Plugin <id>' by `install_plugin`.

## Known gaps

- `models.py` and `manager.py` lack the file header and `__all__`.

## Do not reinvent

Checking whether a plugin is active on an instance (`PluginManager.evaluate_plugins`),
recording per-instance plugin state, or plugin display names (`KNOWN_PLUGIN_NAMES` in
`manager.py`, not exported).
