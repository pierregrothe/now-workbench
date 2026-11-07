# now-workbench -- Active Work

Last updated: 2026-11-07
Last sync: 2026-11-07
Branch: `main` (local only, not pushed)
Python Version: `3.14.10`

## Current Focus

`main` -- deployed and live at https://workbench.grothe.ca (srv01chambly, Cloudflare Access).
Per-user data, groups and approved sharing, impersonation, attachments and limits, and an
autonomous Otto are all verified end to end against a real instance (Alectri, Australia).
ADR-015 is done: platform / domains / interfaces layers, per-domain repositories, 20
import-linter contracts, 500-line modules. The pre-push gate passes (100% coverage, 53 e2e);
nothing has been pushed yet.

## Recent Changes

(no merge commits; last 5 commits on `main`)
- 9270d47 refactor(ai): one tool loop for the async runner and the sync path
- 7287295 refactor: ADR-015 limits -- 500-line modules, ruff complexity and argument caps
- a6ff65e refactor(interfaces): split the largest modules along their seams
- ceae2fe refactor(instances): one resolve() for 'the named instance or the default'
- ae76be7 refactor: platform, domains and interfaces layers with import contracts (ADR-015)

## Open Blockers

None. `main` passes the pre-push gate; pushing waits only for the owner's go-ahead.

## Next Steps

1. Push `main` when the owner approves.
2. Web components: split the 8 baselined files (>500 lines) under their own ADR (ADR-015 Q4).
3. PRD-002 leftovers: chat feedback row (needs backend storage); restyle Synthesizer, Media
   Capture, Fluent Explorer and the Artifact library cards to ADR-019 measurements.
4. Per-user Claude usage limits for outside testers (per-conversation token budgets exist).
5. Scheduled `workbench backup` on srv01chambly.
6. Optional: move tests under `tests/<layer>/` to mirror the new layout.

## Live-instance notes

- Alectri now holds the deployed demo app "GenAI Agentic Incident Router" (scope
  `x_snc_97de30`, table `x_snc_97de30_ai_routing_log`); every test seed was rolled back.
- Server bundles live in the `workbench-bundles` volume: deploying code does not update them.
