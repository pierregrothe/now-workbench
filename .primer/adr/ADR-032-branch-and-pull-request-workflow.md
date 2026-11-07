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
  GitHub Actions. Versions are CalVer `YYYY.MM.N` (N counts a UTC month's releases from 0),
  the primer changelog engine's scheme and alphaseeker's; the owner chose it over SemVer
  (2026-11-07), so the first release turns 0.1.0 into 2026.11.0. Each PR adds one changelog
  line per user-visible change.
- **No GitHub Action gates a push or a PR.** The local hooks are the enforcement, as on srv02.

## Consequences

- A PR costs one full gate run (`check`) instead of one per push.
- A stamp lives in the local `.git`, so it proves only what ran on this machine.
- Repository settings (branch protection) stay the owner's call. The local guards do not
  stop a push made with `--no-verify`. They also see only the first ref of a push:
  pre-commit hands its pre-push hooks the first branch with new commits. So `git push --all`
  or `git push origin feature/x main` would get `main` past `guard-push` and the stamp skip.
  Push one branch at a time (`git push -u origin <branch>`). Branch protection on GitHub is
  the only complete guard.
- The review record must name a commit of the branch itself (an ancestor of the head that is
  not on `origin/main`). Commits made after that reviewed head are still accepted by `land`,
  while the global `pre-pr-check.sh` demands the exact reviewed head at `gh pr create`.
- The stamp proves the head against the `main` it was tested on. The squash merge onto a newer
  `main` is not re-tested.
- The release workflow is serialized (`concurrency`, no cancel-in-progress). GitHub keeps only
  one pending run, so in a burst of three merges the middle run is dropped. A release merge
  caught that way needs its run re-started by hand. The bump commit and the tag are pushed
  atomically.
