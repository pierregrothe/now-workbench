# now-workbench -- Active Work

Last updated: 2026-11-07
Last sync: 2026-11-07
Branch: `main` (local only, not pushed)
Python Version: `3.14.10`

## Current Focus

`main` -- deployed and live at https://workbench.grothe.ca (srv01chambly, Cloudflare Access).
Per-user data, groups and approved sharing, impersonation, attachments and limits, and an
autonomous Otto are all verified end to end against a real instance (Alectri, Australia).
ADR-015 and ADR-024 are done: platform / domains / interfaces layers, per-domain repositories, 20
import-linter contracts, 500-line modules. The pre-push gate passes (100% coverage, 53 e2e);
nothing has been pushed yet.

## Recent Changes

(no merge commits; last 5 commits on `main`)
- b1dfc53 refactor(web): one InstanceData type; PrefsSection base for preference sections
- 29e0b56 refactor(web): shell keeps navigation only; every web file under 500 lines (ADR-024)
- 136fc68 refactor(web): clone and deploy dialogs leave the demo catalog (ADR-024)
- 600490b refactor(web): settings sections as elements; settings load and reset report failures (ADR-024)
- f7a467c refactor(web): component styles beside their components; split the admin panel (ADR-024)

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
