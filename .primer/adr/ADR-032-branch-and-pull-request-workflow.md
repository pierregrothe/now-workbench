# ADR-032: Branch and Pull-Request Workflow

**Status:** accepted 2026-11-07
**Date:** 2026-11-07
**Builds on:** ADR-005 (governance), ADR-029 (mutation gate)
**Epic:** `.primer/epics/2026.11c-pr-workflow/epic.md`

## Context

Until now every commit went straight onto a local `main`, and 110 commits waited for one push.
The owner's other project (alphaseeker, on srv02chambly) lands every story through a pull
request: a branch per story, a once-per-PR gate that stamps the commit it proved, an adversarial
review record, a squash merge, and a release cut by a bot when a merge closes an epic. The
owner asked for the same workflow here (2026-11-07). The global Claude hooks it relies on
(`pre-pr-check.sh`, `pre-push-guard.sh`, `branch-anchor.sh`) come from the dotfiles repository
and already apply.

## Decision

- **A branch per story** (`feature/`, `bugfix/`, `refactor/`, `docs/`), in the one checkout.
  `guard-branch` refuses a commit on `main`, and `guard-push` refuses a push to it. `main`
  only moves through a merged PR (and the release bot's commit on GitHub).
- **Once-per-PR gate:** `scripts/dev-tools/pr_gate.py check` runs the three slow pre-push
  checks (pytest with the 100% floor, the mutation gate, Playwright) on a clean tree and
  writes `<git-common-dir>/pr-gate-stamps/<sha>.json`. The pre-push hooks run through
  `pr_gate.py run-unless-proven` and skip only when that exact commit is the one being pushed,
  the tracked tree is clean, and the stamp records the check as passed. Any other case runs
  them.
- **Review record:** `.primer/reviews/<branch-with-dashes>.md` with `Head: <sha>`. Because
  that folder exists, the global `pre-pr-check.sh` blocks `gh pr create` on a branch touching
  `src/` until the record covers the reviewed head.
- **Land:** `pr_gate.py land <pr>` refuses a PR whose head has no passing stamp, or whose
  record names no ancestor of the head. It then squash-merges, waits for the release run,
  switches to `main` and fast-forwards it.
- **Merge subjects:** a prepare-commit-msg hook rewrites git's `Merge ...` subject to
  `chore(merge): Merge ...` so local merges pass the strict commit-msg gate.
- **Releases (story 02):** a merge that flips an `epic.md` to complete, or that carries the
  `release` label, bumps the version, rolls `CHANGELOG.md`, tags and publishes a release from
  GitHub Actions. The bump is minor for an epic and patch for a label. Each PR adds one
  changelog line per user-visible change.
- **No GitHub Action gates a push or a PR.** The local hooks are the enforcement, as on srv02.

## Consequences

- A PR costs one full gate run (`check`) instead of one per push.
- A stamp lives in the local `.git`, so it proves only what ran on this machine.
- Repository settings (branch protection) stay the owner's call. The local guards do not
  stop a push made with `--no-verify`.
