# Epic: Branch and pull-request workflow

Phase: 2026.11c
Date: 2026-11-07
Source: owner request 2026-11-07 -- reproduce the srv02chambly (alphaseeker) workflow here
Board: EPIC-019
Progress: 2/2 stories done -- COMPLETE

## Goal

Work lands on `main` only through a pull request: a branch per story, a once-per-PR gate that
stamps the commit it proved, a review record, a squash merge, and a release cut by a bot when a
merge closes an epic.

## Requirements Inventory

### Functional Requirements

- FR1: No commit or push straight to `main`; a story works on its own branch
- FR2: `pr_gate.py check` runs the pre-push suite once and stamps the commit; a push of that commit skips the rerun
- FR3: `pr_gate.py land <pr>` refuses an unproven head, squash-merges, waits for the release run, brings `main` current
- FR4: A review record per branch, required by the global PR gate before `gh pr create`
- FR5: A merge that closes an epic (or carries the `release` label) bumps the version, rolls the changelog, tags and publishes a release
- FR6: One-line changelog entries per user-visible PR, validated; weekly dependency audit

### Non-Functional Requirements

- NFR1: No GitHub Action gates a push or a PR; the local hooks are the enforcement [Source: srv02 alphaseeker CLAUDE.md]
- NFR2: Tests use real git repositories in tmp_path, no mocks [Source: CLAUDE.md]

### Constraints

- C1: No new runtime dependency [Source: stack.md]
- C2: Push and merge only with the owner's go-ahead [Source: owner instruction]

## Coverage Map

| Requirement | Story | Status |
|-------------|-------|--------|
| FR1 | 01-pr-gate-and-land | done |
| FR2 | 01-pr-gate-and-land | done |
| FR3 | 01-pr-gate-and-land | done |
| FR4 | 01-pr-gate-and-land | done |
| FR5 | 02-release-bot-and-changelog | done |
| FR6 | 02-release-bot-and-changelog | done |

## Story List

| # | Title | Dependencies | Status |
|---|-------|--------------|--------|
| 01 | Branch guard, PR gate stamp, review records and land | none | done |
| 02 | Release bot, changelog and dependency audit | 01 | done |

## Out of Scope

- Branch protection rules on GitHub (repository settings stay the owner's)
- Worktrees per story (srv02 standing ruling: one checkout, a branch per story)
