# capture domain context (Claude-only)

## What this domain does

Takes screenshots (.png) and videos (.webm) of a ServiceNow instance and files them in a demo
bundle's `media/` directory, indexed by `media/captures.json` (newest first). Screenshots are
one Node/Puppeteer run of `chrome_capture.mjs`; videos replay the bundle's declarative
walkthrough (`walkthrough/playbook.json`, ADR-009) through `playbook_runner.mjs`. It also
lists, relabels and deletes captures. It does NOT check who may touch a bundle (the caller
resolves it through the sharing domain first), look up instances or credentials (callers pass
URL, username and password), read preferences, or run the demo pipeline (`demos` drives it).

## Public entry points (all from `now_workbench.domains.capture`)

- `PlaywrightCaptureEngine(bundles_dir)`: `bundles_dir` is a bundles ROOT, not a bundle
  directory; the bundle is `bundles_dir / bundle_id`.
  - async `capture(req, instance_url, wait_timeout_ms=1500, username="", password="",
    release="Xanadu")` -> `CaptureArtifact`; raises `CaptureFailedError` on a failed live
    capture.
  - `list_captures(bundle_id)`, `update_capture(bundle_id, filename, label)`,
    `delete_capture(bundle_id, filename)`, `clear_all_captures(bundle_id)` -> count.
- `CaptureRequest`: bundle, instance id, `target_path`, `media_type` ("screenshot" or
  "video"), label, viewport, `fake_mode`.
- `CaptureArtifact`: one `captures.json` entry; `url` is
  `/api/demos/<bundle>/captures/<file>`, `engine` is `playwright-simulated` or
  `google-chrome-native`, `step_results` holds the playbook steps of a video.
- `CaptureFailedError`: a `RuntimeError`; interfaces map it to HTTP 502 or a CLI exit 1.

## Wiring

- No database, no repository, no `db_session`. State is files only: `media/*` and
  `media/captures.json` under the bundle, plus Playwright storage state at
  `<data_dir>/sessions/<instance id>_session.json` (`PlaywrightPlaybookDriver`, from
  `get_data_dir`).
- Callers: `interfaces/api/captures.py`, `interfaces/ai/tools/captures.py`,
  `interfaces/ai/tools/demos.py`, `interfaces/cli/demos.py`, `interfaces/cli/synthesizer.py`
  and the `demos` domain (`DemoPipelineEngine.record_video_proof`).
- Imports `InstanceRecord` (instances) and `translate_workspace_url` (releases); from
  platform `safe_child`, `dev_script` and `spawn` / `communicate_bounded` /
  `ProcessTimeoutError` from `platform/procs.py`.
- Node scripts: `scripts/dev-tools/chrome_capture.mjs` (240 s cap) and
  `scripts/dev-tools/playbook_runner.mjs` (900 s cap). Both take `--credentials-stdin`.
- Contracts: `acyclic-domains` -- capture sits below `demos` and above `instances` and
  `releases`.

## Invariants and gotchas

- Credentials go to Node on stdin as JSON (`encode_stdin_credentials`), never in argv.
  Keep it that way for any new script.
- Fail closed on live captures: a failed screenshot or video raises `CaptureFailedError` and
  writes no index entry. A placeholder is written ONLY when `fake_mode` is set, and is then
  labelled `playwright-simulated`. The API capture endpoint and the Otto capture tool OR in
  the `capture_fake_mode` preference; they, the CLI (`--fake`) and the demos pipeline pass
  the result through `is_simulated` (instances), so a simulated instance gets a placeholder.
- Access is the caller's job. In the API and Otto, writes go through `resolve_bundle` with
  `write=True` (owner only, ADR-018) and then pass `settings.get_bundles_dir()`; reads pass
  `BundleAccess.root`, which for a shared bundle is the published snapshot root. The CLI
  skips the check (it runs as the operator, `interfaces/cli/main.py`).
- `_media_dir` creates `media/` on every call, reads included.
- `bundle_id` is checked by `safe_child` (raises `UnsafePathError`); filenames are checked
  by hand for `/`, `\\` and `..` and raise `ValueError`. `clear_all_captures` also
  hand-checks `bundle_id` (`ValueError`).
- `delete_capture` also removes same-stem companions (the video's .png thumbnail).
- `target_path` goes through `translate_workspace_url` for the given release, so
  `@workspace/itsm`-style paths resolve per release. Videos ignore `target_path`: the
  playbook's `start_path` is used, though the artifact still records `target_path`.
- `wait_timeout_ms` is accepted but unused by `capture`.
- A video signs in through a synthetic `InstanceRecord` whose `release` is hard-coded
  "Xanadu"; the storage state is keyed by `req.instance_id` (or "default-instance").
- `load_playbook` falls back to a built-in five-step incident walkthrough when
  `playbook.json` is missing OR invalid; a broken playbook is not reported.

## Known gaps

- `release` defaults to "Xanadu"; `interfaces/ai/tools/demos.py` does not pass
  `inst.release`, so Otto's captures translate paths for Xanadu, not the detected release
  (ADR-014 says the release is never guessed).

## Do not reinvent

- Bounded Node subprocesses with stdin credentials: `spawn` + `communicate_bounded` +
  `encode_stdin_credentials`.
- Release-aware ServiceNow UI paths: `translate_workspace_url` (releases domain).
- Reading a bundle's capture index: `list_captures` (`BundleManager.inspect_bundle` also reads
  `captures.json` raw for its summary; do not add a third reader).
- Safe bundle and file paths: `safe_child`.
