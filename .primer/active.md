# now-workbench -- Active Work

Last updated: 2026-11-07
Last sync: 2026-11-07
Branch: `main` (local only, not pushed)
Python Version: `3.14.10`

## Current Focus

Story in progress: `.primer/epics/2026.11a-tester-safeguards/02-usage-allowance-settings.story.md` (EPIC-017, STORY-055).

`main` -- deployed and live at https://workbench.grothe.ca (srv01chambly, Cloudflare Access).
Per-user data, groups and approved sharing, impersonation, attachments and limits, and an
autonomous Otto are all verified end to end against a real instance (Alectri, Australia).
ADR-015 and ADR-024 to ADR-028 are done (Otto: 76 tools, a `show` tile catalog with charts, telemetry, drives the UI and confirms in words; an Actions screen runs every capability by hand): platform / domains / interfaces layers, per-domain repositories, 20
import-linter contracts, 500-line modules. The pre-push gate passes (100% coverage, 68 e2e);
nothing has been pushed yet.

## Recent Changes

(no merge commits; last 5 commits on `main`)
- 9cc982a feat(web): render Otto's text as HTML through a safe markdown subset (ADR-028)
- 27f6543 feat(telemetry): record every action run and Claude call, and chart them (ADR-028)
- 50f2b07 chore(primer): sync project context
- 850f0de fix(otto): chart requests Otto gets right the first time
- f41c047 feat(otto): chart tiles and history tools (ADR-027)

## Open Blockers

None. `main` passes the pre-push gate; pushing waits only for the owner's go-ahead.

## Next Steps

1. Push `main` when the owner approves.
2. Remaining ADR-013 offline-fallback audit list (components outside the deep-fix scope).
3. PRD-002 leftovers: chat feedback row (needs backend storage); restyle Synthesizer, Media
   Capture, Fluent Explorer and the Artifact library cards to ADR-019 measurements.
4. Per-user Claude usage limits for outside testers: telemetry now records usage per person
   (ADR-028), so caps can be enforced from it.
5. Decide whether mutation testing (mutmut, forkserver mode) becomes a standing gate.
6. Scheduled `workbench backup` on srv01chambly (with a telemetry retention policy).
7. Optional: move tests under `tests/<layer>/` to mirror the new layout.

## Live-instance notes

- Alectri now holds the deployed demo app "GenAI Agentic Incident Router" (scope
  `x_snc_97de30`, table `x_snc_97de30_ai_routing_log`); every test seed was rolled back.
- Server bundles live in the `workbench-bundles` volume: deploying code does not update them.
