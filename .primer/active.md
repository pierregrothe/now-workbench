# now-workbench -- Active Work

Last updated: 2026-11-06
Last sync: 2026-11-06
Branch: `main`
Python Version: `3.14.10`

## Current Focus

`main` -- post-EPIC-016 hardening: live media capture against real instances and platform
release compatibility (minimum-release validation, workspace evolution). No epic in flight;
EPIC-014/015/016 are done. Capability inventory lives in progress.md.

## Recent Changes

(no merge commits; last 5 commits on `main`)
- fc7adb3 feat(ui): display minimum release requirement in catalog cards and modal
- 0d9a2ee feat(releases): add minimum platform version validation and workspace evolution resolver
- 76ec279 feat(capture): enable natural video duration and respect playbook wait pacing
- 2a14288 feat(capture): remove cursor label badge and record clean pointer demo
- c06ea93 feat(doctor): inspect database credentials and record Otto live pipeline proof

## Open Blockers

1. Pre-push gate fails while online: `test_workbench_settings_api_and_cli` sends a non-test
   API key that triggers a live Anthropic probe (401 -> HTTP 400). Passes only offline.
   See progress.md Known Issues for the fix options.

## Next Steps

1. Fix the network-dependent settings test (use an `sk-ant-test` key or inject a fake client).
2. Decide next product direction: no roadmap.md or epics/ exist yet -- consider
   `/primer roadmap` or `/primer brainstorm`.
