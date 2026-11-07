# runbooks domain context (Claude-only)

## What this domain does

Parses a bundle's presenter script (`walkthrough/guide.md`, else `guide.md` at the bundle
root) into a `RunbookGuide`: title, narrative, numbered stages with instructions, talking
points, persona and a target table. It can then check each stage against an instance with
one Table API GET. It does NOT write guides (`synthesizer` generates them), run the browser
walkthrough (`walkthrough/playbook.json` belongs to `capture`), rename tables into an app
scope (`demos` applies the ADR-022 table map before testing), or store anything.

## Public entry points (all from `now_workbench.domains.runbooks`)

- `RunbookEngine()`: stateless, no constructor arguments.
  - `load_runbook(bundle_path, bundle_id="")` -> `RunbookGuide` or None (no guide file).
  - `parse_markdown(content, bundle_id)` -> `RunbookGuide` (pure; use it for text in hand).
  - async `verify_stage(stage, instance, client=None, fake_mode=False)` -> `(passed, message)`.
  - async `test_runbook(guide, instance, client=None, fake_mode=False)` ->
    `RunbookTestResult`; stages run one after another.
- Models: `RunbookGuide`, `RunbookStage`, `DemoPersona`, `RunbookTestResult` (its `stages` are
  `StageTestResult`, which is not exported).

## Wiring

- No database, repository or `db_session`; only `InstanceRecord` from `instances` and
  `httpx` (an `httpx.AsyncClient` with a 10 s timeout unless one is injected through `client`).
- Callers: the `demos` domain (`DemoPipelineEngine` stage count and `test_demo_script`),
  `interfaces/api/demos.py` (the runbook endpoint returns `RunbookGuide`; the verify-stage
  endpoint calls `verify_stage`), `interfaces/cli/bundles.py` (also `verify_stage`),
  `interfaces/ai/tools/bundles.py` and `interfaces/ai/tools/operations.py` (`verify_stage`
  for one stage).
- API and Otto find the bundle directory through the sharing domain (`require_bundle`,
  `bundle_path`); the CLI joins `settings.get_bundles_dir()` itself. The engine trusts the
  path it gets.
- Contracts: `acyclic-domains` -- depends only on `instances`; `demos` sits above it.

## Parser rules (what `parse_markdown` recognises)

- The first `# ` line is the title (a leading "Demonstration Guide:" is dropped).
- A `## ` header whose text has "narrative" or "value" starts the narrative; one with
  "step", "walkthrough" or "stage" starts the steps; anything else is ignored.
- In the steps section a stage starts at a line like `Step 2: ...`, `2. ...` or
  `### Step 2: **Title**`; following lines belong to it.
- Persona: `impersonate **Name**` or `as **Name**` (no word boundary, so `has **x**` also
  matches), optionally followed by the email in parentheses, wrapped in backticks. A
  `**Persona:** Name` line is NOT recognised.
- Target table: per line, the first backticked word (3-40 characters of A-Z, a-z, 0-9 or
  underscore); it counts only if it has an underscore or is `incident`, `change_request` or
  `problem`. The first line that yields one wins. A stage with a table gets the query
  `^ORDERBYDESCsys_created_on`.
- Talking points are lines starting with "show", "notice", "point to/out", "explain",
  "narrate" or "ticket #"; everything else is an instruction.

## Invariants and gotchas

- Verification fails OPEN on content: HTTP 200 passes the stage even with zero rows ("table
  accessible"). It proves the table exists and is readable, not that seed data is there.
  Non-200 or any exception fails the stage, never raises.
- Simulation (`is_simulated` from instances) passes every stage. A stage
  without a target table passes with no call.
- `test_runbook` reports `all_passed=False` for a guide with no stages; `demos` short-circuits
  that case to True itself.
- `load_runbook` returns None both when no guide exists and when reading or parsing raises:
  callers cannot tell "absent" from "broken".
- The synthesizer's own guide marks talking points as `*Talking Point:*` and personas as
  `**Persona:**`; neither matches the rules above, so those lines parse as instructions and
  stages get no persona.

## Do not reinvent

- Guide parsing for any consumer (UI, Otto tiles, CLI): `parse_markdown` / `load_runbook`.
- A Table API readability check for a table: `verify_stage`. Plugin checks live in
  `PluginManager.evaluate_plugins`; property reads in `PropertyEngine.read_live_values`.
- Applying a table rename to stages: `DemoPipelineEngine.test_demo_script` does it with
  model_copy.
