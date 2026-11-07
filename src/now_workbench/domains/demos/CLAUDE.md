# demos domain context (Claude-only)

## What this domain does

The orchestrator at the top of the domain order (ADR-015). `DemoPipelineEngine` evaluates a
bundle against an instance, then runs the whole proof pipeline: release gate, required
plugins, system properties, Fluent app deploy plus seed (ADR-022), runbook stage checks and a
video proof. Each step delegates to the domain that owns it. It does NOT own storage or
tables, check bundle access (callers resolve it through the sharing domain), pick the
instance or read preferences (interfaces do), parse bundles (`bundles`, `runbooks`), talk to
the Table API itself, or build SDK projects (`platform/sdk/project.py`).

## Public entry points (all from `now_workbench.domains.demos`)

- `DemoPipelineEngine(bundles_dir, conn)`: `bundles_dir` is a bundles ROOT; `conn` is a
  `sqlite3.Connection`. Steps, each usable alone:
  - `evaluate_bundle(bundle_id, instance, fake_mode)` -> `DemoEvaluationResult` (sync).
  - `install_required_modules(...)` -> list of `PluginRecord` (sync).
  - async `configure_properties(...)` -> `PropertyApplyResult`.
  - async `deploy_and_seed(...)` -> `(SeedOperationRecord, deploy note, table map)`.
  - async `test_demo_script(..., table_map)` -> `RunbookTestResult`.
  - async `record_video_proof(...)` -> `CaptureArtifact`.
  - async `run_full_pipeline(bundle_id, instance, fake_mode, record_video=True)` ->
    `DemoPipelineSummary`.
- `DemoEvaluationResult`: required / missing / installed plugins, release compatibility,
  property and seed counts, target tables, stage count, `is_ready`.
- `DemoPipelineSummary`: `status` is "success", "partial", "failed" or "incompatible", with a
  human `message`.

## Wiring

- Holds `BundleManager`, `PluginManager` (over `conn`), `PropertyEngine`, `RunbookEngine`
  and `PlaywrightCaptureEngine`; builds a `SeedEngine` over `conn` per deploy. Also uses
  `evaluate_release_prerequisites` (releases) and `InstanceRecord` (instances).
- Platform: `prepare_project` / `SdkProject` / `SdkProjectError` and `NowSdkRunner` from
  `platform/sdk`, `safe_child`, `settings.workspace_dir`.
- Callers: `interfaces/api/demos.py` (evaluate, pipeline), `interfaces/ai/tools/demos.py`
  and `interfaces/cli/demos.py`. They resolve the instance and pass `sdk_fake_mode` (API),
  the tool context's fake mode (Otto) or `--fake` (CLI) as `fake_mode`. The CLI uses
  `settings.get_bundles_dir()` with no sharing check.
- Contracts: `acyclic-domains` -- nothing imports demos except interfaces, which keeps
  `bundles` a leaf.

## Invariants and gotchas

- Access is the caller's: reads pass `BundleAccess.root`, the pipeline first calls
  `resolve_bundle` with `write=True` (owner only, ADR-018) because it records media into
  the bundle, then passes `settings.get_bundles_dir()`.
- `conn` must run inside an owner scope: `SeedEngine` writes owner-scoped seed operations
  and `current_owner` raises `NoOwnerError` outside one (fails closed).
- `run_full_pipeline` returns a summary instead of raising for an incompatible release, a
  failed property apply and a `PipelineStepError` (deploy). A missing bundle still raises
  `FileNotFoundError`; callers map it to 404.
- Missing plugins do NOT stop the pipeline; only the release gate, a failed property apply or
  a deploy error does. "Install" activates nothing on a live instance:
  `PluginManager.install_plugin` only records a plugin it finds active (or any plugin when
  simulated). The summary goes "partial" if any are still missing.
- A `CaptureFailedError` is kept as a note (`status` "partial"), not raised.
- Deploy order (ADR-022): no `package.json` and no `fluent/*.now.ts` skips deploy; a
  simulated instance (`is_simulated`) never deploys, SDK project or not, and is seeded in
  fake mode; otherwise a bundle with `package.json` is installed as is, or the vendor prefix
  "glide.appcreator.company.code" is read live and a project is generated. The returned
  table map renames seed tables and runbook `target_table`s.
- The video proof is a placeholder whenever the instance is simulated.
- `evaluate_bundle` runs twice per pipeline (start and end) and, like
  `install_required_modules`, makes blocking `httpx.Client` plugin queries; inside the async
  pipeline they stall the event loop.
- Seed file parse errors are swallowed in `evaluate_bundle` (counts just drop).
- An empty runbook counts as passed here (`all_passed=True`), unlike `test_runbook`.
- `pipeline.py` is about 430 lines against the 500-line cap.

## Do not reinvent

- Per-step engines: `PluginManager.evaluate_plugins`, `PropertyEngine.apply_bundle_properties`,
  `SeedEngine.load_and_seed`, `RunbookEngine.test_runbook`, `PlaywrightCaptureEngine.capture`.
- Release gating: `evaluate_release_prerequisites`. Scope and table renaming:
  `prepare_project`, `scope_for`, `table_map_for`.
- Reading live property values: `PropertyEngine.read_live_values`.
