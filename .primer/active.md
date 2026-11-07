# now-workbench -- Active Work

Last updated: 2026-11-07
Last sync: 2026-11-07
Branch: `main` (local only, not pushed)
Python Version: `3.14.10`

## Current Focus

`main` -- deployed and live at https://workbench.grothe.ca (srv01chambly, Cloudflare Access).
Per-user data, groups and approved sharing, impersonation, attachments and limits, and an
autonomous Otto are all verified end to end against a real instance (Alectri, Australia).
ADR-015, ADR-024 and ADR-025 are done (Otto: 59 tools incl. sharing and admin, a `show` tile catalog): platform / domains / interfaces layers, per-domain repositories, 20
import-linter contracts, 500-line modules. The pre-push gate passes (100% coverage, 53 e2e);
nothing has been pushed yet.

## Recent Changes

(no merge commits; last 5 commits on `main`)
- 1399d16 feat(web): render Otto's catalog tiles with the app's own elements (ADR-025)
- 95bb2cb feat(otto): sharing and admin tools, and a show tool for visual tiles (ADR-025)
- 7f3b433 refactor(domains): sharing, group and team rules move into domain services (ADR-025)
- b3bda0e chore(primer): sync project context
- b1dfc53 refactor(web): one InstanceData type; PrefsSection base for preference sections

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
