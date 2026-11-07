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
  - async `capture(req, instance_url, *, release, wait_timeout_ms=1500, username="",
    password="")` -> `CaptureArtifact`; `release` is required (the instance's detected
    `InstanceRecord.release`, ADR-014). Raises `CaptureFailedError` on a failed live capture
    and its subclass `UnknownReleaseError` on a live capture whose release is undetected.
  - `list_captures(bundle_id)`, `update_capture(bundle_id, filename, label)`,
    `delete_capture(bundle_id, filename)`, `clear_all_captures(bundle_id)` -> count.
- `CaptureRequest`: bundle, instance id, `target_path`, `media_type` ("screenshot" or
  "video"), label, viewport, `fake_mode`.
- `CaptureArtifact`: one `captures.json` entry; `url` is
  `/api/demos/<bundle>/captures/<file>`, `engine` is `playwright-simulated` or
  `google-chrome-native`, `step_results` holds the playbook steps of a video.
- `CaptureFailedError`: a `RuntimeError`; interfaces map it to HTTP 502 or a CLI exit 1.
- `UnknownReleaseError`: a `CaptureFailedError`; the API maps it to HTTP 409 (a fixable
  precondition, like "No target instance"); the CLI, Otto and the pipeline treat it as its base.

## Wiring

- No database, no repository, no `db_session`. State is files only: `media/*` and
  `media/captures.json` under the bundle, plus Playwright storage state at
  `<data_dir>/sessions/<instance id>_session.json` (`PlaywrightPlaybookDriver`, from
  `get_data_dir`).
- Callers: `interfaces/api/captures.py`, `interfaces/ai/tools/captures.py`,
  `interfaces/ai/tools/demos.py`, `interfaces/cli/demos.py`, `interfaces/cli/synthesizer.py`
  and the `demos` domain (`DemoPipelineEngine.record_video_proof`).
- Imports `InstanceRecord` (instances), `translate_workspace_url` and `is_release_detected`
  (releases); from platform `safe_child`, `dev_script` and `spawn` / `communicate_bounded` /
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
- Every caller (API, Otto, CLI, `record_video_proof`) passes the instance's detected release;
  nothing defaults to a release. A screenshot's `target_path` is given exactly one leading
  `/` and then goes through `translate_workspace_url`, so slash-less and slashed paths alike
  and `@workspace/itsm`-style tokens resolve per release; a full `http(s)://` URL keeps its
  form (`_translate`).
- An undetected release ("", "Unknown") is never guessed: a live capture raises
  `UnknownReleaseError` naming the gap (run a connection test) before any browser starts; a
  simulated capture still writes its placeholder and records the path rooted, untranslated.
- A video replays the playbook, not `target_path`: the playbook's `start_path` and every step
  `path` are translated for the release, and the artifact records the translated
  `start_path` (the page the video actually opened), fake mode included.
- `wait_timeout_ms` (the `capture_wait_timeout_ms` preference, 0..30000, default 1500; the
  API, Otto and the CLI pass it) is the screenshot's page settle, passed to
  `chrome_capture.mjs` as `--settle-ms`. The script's exported argument parser clamps it
  to 0..30000 and defaults to 1500; the script only runs its capture when executed, so tests
  import the parser. Videos dwell per playbook step.
- A video signs in through a synthetic `InstanceRecord` carrying the given release; the
  storage state is keyed by `req.instance_id` (or "default-instance").
- `load_playbook` falls back to a built-in five-step incident walkthrough when
  `playbook.json` is missing OR invalid; a broken playbook is not reported.

## Known gaps

- A video's `CaptureRequest.target_path` has no effect, so the `target_path` argument of
  `DemoPipelineEngine.record_video_proof` (demos) does nothing.

## Do not reinvent

- Bounded Node subprocesses with stdin credentials: `spawn` + `communicate_bounded` +
  `encode_stdin_credentials`.
- Release-aware ServiceNow UI paths: `translate_workspace_url` (releases domain).
- Reading a bundle's capture index: `list_captures` (`BundleManager.inspect_bundle` also reads
  `captures.json` raw for its summary; do not add a third reader).
- Safe bundle and file paths: `safe_child`.
