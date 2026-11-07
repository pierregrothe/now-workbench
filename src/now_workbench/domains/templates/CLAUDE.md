# templates domain context (Claude-only)

## What this domain does

Customisation templates: a stored record that points at a base demo bundle, and an engine
that copies that bundle into a new bundle directory for one customer, substituting fixed
placeholders (customer name, colours, logo URL, assignment group) in its text files and
rewriting its `manifest.json` id and name. It does NOT list, validate or register bundles
(`bundles`, and the bundle registry in `sharing`), deploy or seed them (`demos`, `seed`),
or apply `parameters_schema` (it is stored and returned, never used by the engine).

## Public entry points (all from `now_workbench.domains.templates`)

- `TemplateRepository` -- `list_templates()` (all rows, no order), `save_template(tmpl)`
  (upsert by id). There is no get-by-id or delete; callers build
  `{t.id: t for t in list_templates()}` and look up.
- `TemplateEngine(bundles_dir, output_dir)` -- `instantiate(base_bundle_id, request)` ->
  path of the new bundle directory.
- `TemplateRecord` -- id, name, description, version, `base_bundle_id`,
  `parameters_schema` (a dict, stored as JSON).
- `TemplateInstantiationRequest` -- `target_bundle_id`, `customer_name`, and defaults for
  `primary_color`, `secondary_color`, `logo_url`, `assignment_group`.

## Wiring

- Table: templates (id primary key, `parameters_schema` checked as valid JSON). It is
  global: no owner column, no owner scoping.
- `TemplateEngine` needs no connection.
- Imports only platform: `safe_child` and `UnsafePathError` from
  `platform/config/paths.py`.
- Callers: `interfaces/api/templates.py` (list, instantiate), `interfaces/cli/templates.py`
  (list, generate, inspect), `interfaces/ai/tools/bundles.py` (Otto's list and generate
  tools), and `seed_database` in `interfaces/api/app.py`, which saves the one built-in
  template (`agentic-router-template`, base bundle `template-customer-service-ai`) at
  startup when the table is empty.
- Output directory differs by caller: the API and Otto write to `settings.workspace_dir`;
  the CLI writes back into the bundles directory (`output_dir=bundles_dir`).

## Invariants and gotchas

- Path safety: both the base id and the target id go through `safe_child` (a direct child
  of its root, no separators or `..`), and a target that resolves to the base bundle raises
  `UnsafePathError`. A missing base raises `FileNotFoundError`.
- DESTRUCTIVE: an existing target directory is deleted (`shutil.rmtree`) before the copy.
  Instantiating twice with the same `target_bundle_id` silently replaces the first result.
- Substitution touches only files ending .json, .ts, .js, .md or .txt; the placeholders are
  the fixed set `{{customer_name}}`, `{{customer_name_clean}}` (lower-cased, non
  `[a-zA-Z0-9_]` replaced by `_`), `{{primary_color}}`, `{{secondary_color}}`,
  `{{logo_url}}`, `{{assignment_group}}`. `parameters_schema` does not drive it.
- Every file named `manifest.json` anywhere in the copied tree is re-serialised (indent 2)
  with `id` set to the target id and `name` prefixed with the customer name; one that is not
  valid JSON after substitution is written as plain text instead (the error is swallowed).
- No role check anywhere in the domain or its routes: any signed-in person may list and
  instantiate. Templates are shared by everyone.
- The engine registers nothing. `sync_registry` (in `sharing`) only scans
  `settings.get_bundles_dir()`, so a CLI result (written there) is registered at the next
  sync, while an API or Otto result (written under `settings.workspace_dir`) is not.

## Do not reinvent

- Copying a bundle under a new id with placeholder substitution: `TemplateEngine`.
- Untrusted ids to filesystem paths: `safe_child`, never manual joins.
