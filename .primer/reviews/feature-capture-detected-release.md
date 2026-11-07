# Review record -- feature/capture-detected-release

- Head: d88d6e0f01567f838f6e5e5d83d352110dc37d87
- Branch: `feature/capture-detected-release`
- Date: 2026-11-07
- Scope: EPIC-021 story 03.
  - Every capture call site passes the instance's detected release, and `release` is required with no "Xanadu" default.
  - A live capture with an undetected release raises `UnknownReleaseError` (HTTP 409) instead of guessing (ADR-014). Simulated captures keep the path untranslated.
  - Paths get exactly one leading slash before translation.
  - `wait_timeout_ms` reaches `chrome_capture.mjs` as `--settle-ms` and is clamped to 0..30000. The CLI reads the preference, stored values are clamped on load, and the web field accepts 0.
  - Video records show the translated playbook start.
- Process: top-tier implementer (red first: 16, then 19 failing tests); one Sonnet adversarial review.
  - No BLOCKING.
  - 1 MAJOR, a test gap: the pipeline call site was unpinned, and a mutant passing "Xanadu" survived.
  - MINOR: slash-less legacy paths stopped translating; the Node parse was only grep-tested; the wait was unbounded; the CLI ignored the preference; there were three different defaults; a 502 was returned for a fixable precondition.
  - All fixed in 442a04c, d6173c0 and the web fix: a pinned pipeline test and a wider source scan; `_rooted` before and after translation; a real Node parser test with clamps; one 1500 default; the CLI uses the preference; clamp on load; 409.

## Verified

- 100% coverage. The reviewer's mutants on the API, Otto, CLI and engine were killed, and the pipeline mutant is now covered.
- The Dockerfile still ships `chrome_capture.mjs`; `node --check` and `tests/test_capture_tls.py` pass.

## Not done (follow-ups)

- A video ignores `CaptureRequest.target_path`, so `record_video_proof`'s `target_path` argument does nothing (demos domain).
- The mjs `--mode video` path is dead code; Python never asks the script for video.
