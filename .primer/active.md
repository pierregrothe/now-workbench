# now-workbench -- Active Work

Last updated: 2026-11-06
Last sync: 2026-11-06
Branch: `main` (local only, not pushed)
Python Version: `3.14.10`

## Current Focus

`main` -- deployed and live at https://workbench.grothe.ca (srv01chambly, Cloudflare Access).
Per-user data, groups and approved sharing, impersonation, attachments and limits, and an
autonomous Otto are all verified end to end against a real instance (Alectri, Australia).
The pre-push gate passes (100% coverage); nothing has been pushed yet.

## Recent Changes

(no merge commits; last 5 commits on `main`)
- b484a59 fix: bounded subprocesses, shared Claude client, export cleanup, slimmer image, container limits
- e0a3350 feat(otto): cache conversations byte for byte; compaction; token budgets per conversation
- 12b5d06 chore(primer): sync project context
- 369e35a fix(ui): conversation counters show questions asked against the admin limit
- 1296d73 feat(pipeline): deploy a demo's Fluent app into the instance's vendor scope

## Open Blockers

None. `main` passes the pre-push gate; pushing waits only for the owner's go-ahead.

## Next Steps

1. Push `main` when the owner approves.
2. ADR-015 (proposed): settle its open questions, accept, restructure in small green steps
   (held findings reuse-001/002, rules-003 belong there).
3. PRD-002 leftovers: chat feedback row (needs backend storage); restyle Synthesizer, Media
   Capture, Fluent Explorer and the Artifact library cards to ADR-019 measurements.
4. Per-user Claude usage limits for outside testers (per-conversation token budgets exist).
5. Scheduled `workbench backup` on srv01chambly.
6. Remove the orphaned `/app/workspaces/sdk-toolchain` (347 MB) on srv01chambly once the
   owner confirms; the image now ships the SDK globally.

## Live-instance notes

- Alectri now holds the deployed demo app "GenAI Agentic Incident Router" (scope
  `x_snc_97de30`, table `x_snc_97de30_ai_routing_log`); every test seed was rolled back.
- Server bundles live in the `workbench-bundles` volume: deploying code does not update them.
