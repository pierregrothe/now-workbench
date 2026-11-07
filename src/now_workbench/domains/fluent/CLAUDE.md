# fluent domain context (Claude-only)

## What this domain does

Reads ServiceNow Fluent SDK sources (`*.now.ts`) in a demo bundle and extracts each
`Table({ ... })` declaration as a `FluentTableSchema` (name, label, columns), then diffs two
table sets structurally (ADR-008). It is a pure-Python regex and balanced-brace scanner: no
TypeScript parser, no Node, no subprocess, despite the "AST" in its docstrings. It does NOT
build, deploy or rename tables into an app scope (`prepare_project`, `table_map_for` and
`NowSdkRunner` in `platform/sdk`, driven by `demos`), check bundle access (callers do), or
write any file.

## Public entry points (all from `now_workbench.domains.fluent`)

- `FluentEngine()`: stateless.
  - `load_bundle_schemas(bundle_path)` -> list of `FluentTableSchema`, from every
    `**/*.now.ts` under the bundle, files in sorted order; [] when the path does not exist.
  - `parse_source(content)` -> list of `FluentTableSchema` for one source text.
  - `compute_diff(schemas_a, schemas_b)` -> `FluentSchemaDiff` (B relative to A).
- `FluentTableSchema`: `name`, `label`, `columns`, `raw_source` (the whole block).
- `FluentColumnDef`: `name`, `label`, `column_type`, `reference`, `mandatory`, `max_length`.
- `FluentSchemaDiff`: `added_tables`, `removed_tables` (both sorted),
  `modified_tables` (table -> human-readable change lines), `identical`.

## Wiring

- Imports nothing from other domains or platform; no database, repository or `db_session`.
- Callers: `interfaces/api/demos.py` (`GET /api/demos/<id>/fluent` and
  `POST /api/demos/<id>/fluent/diff`, which feed the Fluent explorer tab),
  `interfaces/ai/tools/bundles.py` (Otto schema and diff tiles) and `interfaces/cli/fluent.py`.
- API and Otto resolve paths through the sharing domain first (`require_bundle` in the API,
  `bundle_path` in Otto tools), so a shared bundle is read from its published snapshot; the
  CLI does not.
- Contracts: `acyclic-domains` -- a leaf domain.

## Invariants and gotchas

- Column type is only ever "reference" (when a `reference:` string key is found) or
  "string". The column constructor (IntegerColumn, BooleanColumn, ...) is matched but not
  recorded, so type changes between non-reference columns are invisible to the diff.
- The reference key must be literally `reference:`; the synthesizer's generated sources use a
  referenceTable key, so their reference columns come out as "string" with no reference.
- Columns are any `<name>: Record({` or `<name>: <Word>Column({` inside the table block.
  Column bodies use a string-aware brace matcher (`_find_balanced_close`); the outer table
  scan (`_extract_table_blocks`) does NOT skip strings, so a `{` or `}` inside a quoted
  string in a table block can cut or extend that block.
- The table name is the first quoted `name:` in the block; a block without one is skipped.
  A quoted value is cut at its first inner quote ("Bob's Case" reads as Bob).
- For columns present in both tables the diff compares type, reference and mandatory only;
  label and `max_length` changes are not reported (added and removed columns are). Tables
  are matched by name, so a renamed table is one removal plus one addition.
- Read and parse errors on a file are swallowed (`continue`): a broken file yields no tables
  and no error.
- File discovery differs by consumer: this engine reads `**/*.now.ts` from the bundle root;
  `BundleManager.inspect_bundle` reads `fluent/**/*.now.ts`; deploy (`prepare_project`,
  `deploy_and_seed`) reads only `fluent/*.now.ts`. A table in `fluent/sub/` is shown and
  diffed but never deployed.

## Do not reinvent

- Listing a bundle's tables or columns: `load_bundle_schemas`; for text in hand,
  `parse_source`.
- Comparing two bundles' data models: `compute_diff`.
- Table names for scope renaming are found by a separate regex in `platform/sdk/project.py`
  (`table_map_for`); deploy-time renaming belongs there, not here.
