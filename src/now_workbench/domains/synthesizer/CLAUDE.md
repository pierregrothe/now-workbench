# synthesizer domain context (Claude-only)

## What this domain does

Turns a one-line use case and customer context into a new demo bundle on disk (ADR-003
layout): `manifest.json`, one Fluent table in `fluent/<bundle>.now.ts`, three seed records,
`properties/sys_properties.json` and a presenter guide `walkthrough/guide.md`. Everything is
string templates; no model or network call is made. It also resolves which release to build
for. It does NOT register the new bundle's owner (callers call `register_new_bundle` from
the sharing domain), deploy or seed it (`demos`), parse what it wrote (`fluent`, `runbooks`,
`bundles`), or read preferences (callers pass author and scope prefix).

## Public entry points (all from `now_workbench.domains.synthesizer`)

- `UseCaseSynthesizer(bundles_dir)`: `synthesize(req, author_name=..., scoped_prefix="x_snc")`
  -> `SynthesizedDemoResult` (bundle id and path, table name, generated Fluent code, seed
  records, properties, guide markdown). Raises `ValueError` when `req.sn_release` is None.
- `UseCaseSynthesisRequest`: `use_case` (required), customer, industry, optional
  `bundle_id`, `sn_release`, `instance_id`, brand colour, two "Name (Role)" personas.
- `resolve_synthesis_release(conn, explicit, instance_id)` -> release name: the explicit
  value, else the target (or default) instance's detected profile release.
- `NoReleaseError`: no explicit release and no instance with a detected release.
- `SynthesizedDemoResult`: the response model of the synthesize endpoint.

## Wiring

- `resolve_synthesis_release` needs a connection; it builds an `InstanceRepository`
  (`resolve`, `get_instance_profile`) and compares against `UNKNOWN_RELEASE` from `releases`.
  The engine itself has no repository and only uses `safe_child` from platform.
- Callers: `interfaces/api/demos.py` (404 on `LookupError`, 409 on `NoReleaseError`),
  `interfaces/ai/tools/bundles.py` and `interfaces/cli/synthesizer.py`. API and Otto pass
  `sc_author_name` and `default_scoped_prefix` from the preferences and then call
  `register_new_bundle` with `current_owner`; the CLI relies on the CLI's own end-of-command
  registration (`sync_registry` when each command closes).
- All callers pass `settings.get_bundles_dir()`: a new bundle always lands in the shared
  bundles root.
- Contracts: `acyclic-domains` -- depends on `instances` and `releases` only.

## Invariants and gotchas

- Never overwrites: if `<bundle_id>` exists (anyone's, ADR-018) it tries `<id>-2`, `<id>-3`, ...
  The returned `bundle_id` may differ from the requested one; always use the returned one.
- The release is never guessed (ADR-014): an `UNKNOWN_RELEASE` profile counts as no release.
  `explicit` wins without checking the instance. A named instance that does not exist raises
  `LookupError`, not `NoReleaseError`.
- An explicit `bundle_id` is only checked by `safe_child` (raises `UnsafePathError`); the
  derived id is a slug cut to 36 characters, "custom-demo" when empty.
- Table name is `<prefix>_<slug, 18 chars>_case`; the prefix is cleaned to `[a-z0-9_]`,
  `x_snc` when empty. `demos` later renames it into the instance's app scope (ADR-022); the
  bundle files are never rewritten.
- The manifest hard-codes `required_plugins` "com.now_assist_core" and "com.snc.incident"
  and placeholder persona emails at example.com.
- The generated Fluent uses a referenceTable key, which the `fluent` parser does not read as
  a reference (it looks for `reference:`), so the explorer shows that column as a string.
- The generated guide keeps its executive narrative above the first `## ` header and marks
  personas as `**Persona:**`; the `runbooks` parser reads neither, so the parsed guide has
  an empty narrative and stages without personas.

## Do not reinvent

- "Which release is this for?": `resolve_synthesis_release`; release ordering and
  workspace paths live in the `releases` domain.
- Bundle id collision handling and safe paths: `synthesize` plus `safe_child`.
- Bundle ownership on creation: `register_new_bundle` (sharing).
