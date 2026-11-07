# now-workbench -- Active Work

Last updated: 2026-11-07
Last sync: 2026-11-07
Branch: `main` (local only, not pushed)
Python Version: `3.14.10`

## Current Focus

`main` -- deployed and live at https://workbench.grothe.ca (srv01chambly, Cloudflare Access).
Per-user data, groups and approved sharing, impersonation, attachments and limits, and an
autonomous Otto are all verified end to end against a real instance (Alectri, Australia).
ADR-015, ADR-024, ADR-025 and ADR-026 are done (Otto: 70 tools, a `show` tile catalog, drives the UI and confirms in words; an Actions screen runs every capability by hand): platform / domains / interfaces layers, per-domain repositories, 20
import-linter contracts, 500-line modules. The pre-push gate passes (100% coverage, 53 e2e);
nothing has been pushed yet.

## Recent Changes

(no merge commits; last 5 commits on `main`)
- 60cc611 fix(otto): the agent runner takes the whole question, so tools know the conversation
- a32543a feat(otto): conversational control of the whole app, and an Actions screen (ADR-026)
- 078086a feat(otto): tiles span one, two or three columns (ADR-025)
- 46fd091 chore(primer): sync project context
- 1399d16 feat(web): render Otto's catalog tiles with the app's own elements (ADR-025)

## Open Blockers

None. `main` passes the pre-push gate; pushing waits only for the owner's go-ahead.

## Next Steps

1. Push `main` when the owner approves.
2. Remaining ADR-013 offline-fallback audit list (components outside the deep-fix scope).
3. PRD-002 leftovers: chat feedback row (needs backend storage); restyle Synthesizer, Media
   Capture, Fluent Explorer and the Artifact library cards to ADR-019 measurements.
4. Per-user Claude usage limits for outside testers (per-conversation token budgets exist).
5. Scheduled `workbench backup` on srv01chambly.
6. Optional: move tests under `tests/<layer>/` to mirror the new layout.

## Live-instance notes

- Alectri now holds the deployed demo app "GenAI Agentic Incident Router" (scope
  `x_snc_97de30`, table `x_snc_97de30_ai_routing_log`); every test seed was rolled back.
- Server bundles live in the `workbench-bundles` volume: deploying code does not update them.
