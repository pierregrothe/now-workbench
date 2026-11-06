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

1. Pre-push gate fails: coverage 90% vs required 100% (see progress.md Known Issues).

## Next Steps

1. Architecture review (ADR-015, proposed): settle its 4 open questions, then accept it and
   restructure into `platform/`, `domains/`, `interfaces/` in small green steps.
2. Then fix review findings (silent failures, UI fallbacks), then raise coverage on the
   final layout (pre-push floor is 100%; currently 91%).
3. Decide next product direction: no roadmap.md or epics/ exist yet -- consider
   `/primer roadmap` or `/primer brainstorm`.
