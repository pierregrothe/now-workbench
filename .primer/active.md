# now-workbench -- Active Work

Last updated: 2026-11-06
Last sync: 2026-11-06
Branch: `main` (local only, not pushed)
Python Version: `3.14.10`

## Current Focus

`main` -- ready for the first container deploy on srv01chambly behind Cloudflare Access
(ADR-016/017, runbook `docs/deploy.md`). Otto-style UI alignment (PRD-002) built; deep-fix
review findings merged.

## Recent Changes

(no merge commits; last 5 commits on `main`)
- e51f974 feat(deploy): first-run setup code, team roles in the database, hardened container
- b2a71a6 feat(auth): Cloudflare Access sign-in with admin and consultant roles; Otto-style icons
- 380778d feat(profile): profile picture, built-in avatars and servicenow.com email-code approval
- e881792 feat(ui): settings left menu, detail side panel, live home tiles, shared tile chrome
- b7d3d71 feat(ui): align chat, tiles and areas to the observed Otto look and feel

## Open Blockers

1. Pre-push gate fails: coverage 93% vs required 100%, so `main` cannot be pushed yet.
2. The container image was never built or run (Docker is not installed on the dev Mac); the
   first `docker compose up` on srv01chambly is its first real test.
3. Cloudflare Access is not configured yet (owner: Google/Apple login methods, Access app for
   the `workbench` hostname, tunnel public hostname, `.env` on the server).
4. A placeholder `.env` (copy of `.env.example`) sits in the repo root; locally it switches
   `workbench serve` into Cloudflare mode. The owner should delete it on the Mac.

## Next Steps

1. Owner deploys per `docs/deploy.md`; read the setup code from `docker logs`, become admin,
   enter the Claude key and instances in the UI. Fix whatever the first build reveals.
2. Raise coverage to the 100% pre-push floor, then push `main`.
3. ADR-015 (proposed): settle its open questions, accept, restructure in small green steps
   (held findings reuse-001/002, rules-003 belong there).
4. PRD-002 leftovers: chat feedback row (needs backend storage), check off its acceptance list.
