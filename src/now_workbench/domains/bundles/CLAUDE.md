# bundles domain context (Claude-only)

## What this domain does

Reads and manages demo bundles on disk (ADR-003): a directory per bundle holding
`manifest.json` plus optional `fluent/`, `seed/`, `properties/`, `walkthrough/` and `media/`
content. It parses a bundle into `DemoBundleInfo`, and lists, clones, exports to a zip,
imports, deletes and edits the manifest of bundles under one storage directory. It does NOT
know who owns or may see a bundle (`sharing`: `resolve_bundle`, `list_accessible`,
`register_new_bundle`, versions), apply anything to an instance (`properties`, `seed`,
`plugins`, `runbooks`, `demos`), or create bundles from scratch (`synthesizer`, `templates`).

## Public entry points (all from `now_workbench.domains.bundles`)

- `BundleManager(storage_dir)` -- creates the directory if missing.
  - `inspect_bundle(bundle_dir)` -> `DemoBundleInfo`; raises `FileNotFoundError` without a
    manifest.
  - `list_bundles()` -- every subdirectory with a manifest, sorted by name.
  - `clone_bundle(source_id, target_id, target_name=None, source_root=None)` -- copies from
    `source_root` (a shared or published root) into this manager's storage.
  - `export_bundle(bundle_id, output_archive)`, `import_bundle(archive_path)`.
  - `delete_bundle(bundle_id)`, `update_bundle_manifest(bundle_id, name, description, tags)`.
- Models: `DemoManifest` (id, name, version, release fields, `required_plugins`, tags,
  personas), `DemoPersona`, `DemoBundleInfo` (manifest, `bundle_path`, file lists, `sys_properties`,
  `media_captures`, and the access fields `owner_email`, `access`, `version`).

## Wiring

- No repository and no tables: this domain is pure filesystem. Ownership rows live in
  `sharing` (`ArtifactRepository`).
- The usual pattern: resolve access first, then point a manager at the root it returns.
  `BundleAccess` gives `root` (the live bundles dir, or a published version root for a shared
  bundle) and `path`; call `BundleManager(storage_dir=access.root)` with it. Writes (clone,
  delete, update) use `settings.get_bundles_dir()` after `resolve_bundle(conn, id, write=True)`.
- `bundle_info` in `interfaces/api/demo_support.py` fills the access fields with
  model_copy; the manager itself leaves them at their defaults.
- Imported by `domains/demos/pipeline.py`, `interfaces/api/demos.py`, `demo_support.py`,
  `replies.py`, `interfaces/ai/tools/bundles.py`, `interfaces/cli/bundles.py`,
  `interfaces/cli/demos.py`.
- It imports only `safe_child` from `platform/config/paths.py`: it is a leaf domain.
- Contracts: `acyclic-domains` -- `demos` imports it, so it must never import `demos`.

## Invariants and gotchas

- No access checks here: every caller must go through `sharing` first. The bundles
  directory is shared by all owners, so a manager on `settings.get_bundles_dir()` sees
  everyone's bundles.
- Ids pass through `safe_child` (raises `UnsafePathError` on separators, `..`, or a symlink
  escape) in clone, export, import, delete and update. `inspect_bundle` takes a path, not an
  id, and does no check.
- Creating a bundle is two steps: the manager writes files, then the caller must
  `register_new_bundle(conn, id, current_owner())` or the bundle has no owner (the CLI
  backfills via `sync_registry` on exit).
- Deleting is three steps in the API and Otto: `delete_bundle`, then
  `forget_artifact` on `ArtifactRepository`, then `delete_artifact_files`.
  `interfaces/cli/demos.py` only does the first.
- `clone_bundle` lower-cases and strips the target id and refuses an existing target
  (`FileExistsError`); delete and update only strip.
- `import_bundle` replaces an existing bundle with the same manifest id (rmtree first), sets
  no owner, and has no callers in src (tests only).
- `list_bundles` skips bundles whose manifest will not parse; `inspect_bundle` raises on a bad
  manifest but treats an unreadable properties file or capture index as empty.
- `inspect_bundle` reads properties only from `properties/sys_properties.json`;
  `PropertyEngine` also accepts the file at the bundle root.
- `DemoManifest` keeps `min_release` and `sn_release` in sync when only one is given.
- `export_bundle` zips every file `rglob` yields, including symlinked files; `sharing` version
  snapshots skip symlinks.

## Do not reinvent

- Parsing a bundle directory (`inspect_bundle`) and safe id-to-path mapping (`safe_child`).
- Access-aware listing and lookup: `list_accessible` and `resolve_bundle` in `sharing`, and
  `require_bundle` / `bundle_info` in `interfaces/api/demo_support.py` for routes.
- Zipping a bundle for download (`export_bundle`); frozen versions (`save_version` /
  `save_new_version` in `sharing`).
