# releases domain context (Claude-only)

## What this domain does

Pure functions over ServiceNow release family names: normalize a name, order two releases,
decide whether an instance release meets a bundle's minimum (plus feature minimums matched
from bundle tags), parse the family from a glide.war build string, and map symbolic
workspace paths to the right URL for a release (Agent Workspace vs SOW, classic vs configurable
CSM, AI Agent Studio). No database, no I/O, no state. It does NOT detect an instance's release
(the instances domain reads the build in `profile.py` and stores the profile, ADR-014), pick
the release to synthesize for (`resolve_synthesis_release` in the synthesizer domain), or
decide demo readiness (the demos pipeline combines this result with plugin checks).

## Public entry points (all from `now_workbench.domains.releases`)

Names and ordering:
- `normalize_release` (name) -> canonical family ("washingtondc", "wdc", "san-diego" all
  map); an unlisted name comes back title-cased, not rejected.
- `compare_releases` (a, b) -> -1, 0 or 1, chronological.
- `is_release_compatible` (instance_release, min_release) -> bool.
- `is_release_detected` (name) -> False for "" or "Unknown" (any case, padded).
- `RELEASE_FAMILIES`: ordered tuple, Rome to Australia. `UNKNOWN_RELEASE`: the "Unknown"
  sentinel instances carry until a connection test reports a release.

Prerequisites:
- `evaluate_release_prerequisites` (instance_release, min_release, tags=None) ->
  `ReleaseCompatibilityResult` (is_compatible, normalized releases, a person-facing reason,
  required_features, unsupported_features).
- `FEATURE_MINIMUM_RELEASES`: feature name -> (minimum release, explanation).

Detection: `BUILD_PROPERTY` ("glide.war"), `parse_release_family` (build) -> family or None.

Workspaces: `resolve_workspace` (workspace_type, release) -> `WorkspaceRoute`;
`translate_workspace_url` (target_path, release) rewrites `@workspace/itsm`, `@workspace/csm`
and `@workspace/ai_studio` tokens, and pre-San Diego rewrites Next Experience and SOW paths to
their legacy forms.

## Wiring

- No repository and no tables; nothing here takes a connection.
- Imports nothing outside its own package (no platform, no other domain). It is a leaf, so
  any domain may import it without risking an acyclic-domains cycle.
- Callers (all domains, no interface imports it directly): instances (`UNKNOWN_RELEASE` in
  `models.py` and `repository.py`; `BUILD_PROPERTY` and `parse_release_family` in
  `profile.py`, the fallback when the glide.build.name property and the cluster build name
  are absent),
  synthesizer (`UNKNOWN_RELEASE` in `release.py`), demos (`evaluate_release_prerequisites`
  in `pipeline.py`), capture (`translate_workspace_url` and `is_release_detected` in `engine.py`).

## Invariants and gotchas

- The family list is for ordering requirement names only (ADR-014). A name not in it ranks
  NEWER than every listed release, so a new ServiceNow release works without a code change;
  but a typo in a bundle's min_release also ranks newest and makes the bundle incompatible with
  every listed release.
- Undetected ("" or "Unknown") ranks OLDEST (-1) and is never compatible: fail closed.
  `evaluate_release_prerequisites` gives it a "run a connection test" reason.
- Because undetected ranks oldest, `resolve_workspace` and `translate_workspace_url` route an
  undetected release to the legacy (pre-San Diego) workspace paths. Capture checks
  `is_release_detected` first and never translates for an undetected release.
- Feature matching is a case-insensitive substring test of the full feature name inside each
  tag ("Fluent SDK" matches a tag "fluent sdk demo", not "fluent"). A feature unsupported on the
  instance makes the whole result incompatible even when the minimum release is met.
- When features are missing, the reason text names the bundle's minimum release, not the
  feature's own minimum.
- `resolve_workspace` falls through to classic navigation for any unrecognised type; HR always
  maps to the Employee Center path regardless of release.

## Known gaps

- `check_feature_compatibility` (compatibility.py) and `WorkspaceCategory` (models.py) have no
  caller in src. `compatibility.py` and `workspaces.py` lack the file header and `__all__`
  the other modules carry.

## Do not reinvent

Release string comparison or normalization of any kind (`compare_releases`,
`normalize_release`), "is this instance new enough" (`is_release_compatible`,
`evaluate_release_prerequisites`), parsing a build identifier (`parse_release_family`), or
release-aware workspace URLs (`translate_workspace_url`).
