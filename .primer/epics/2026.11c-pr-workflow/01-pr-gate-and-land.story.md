# Story 2026.11c.01: Branch guard, PR gate stamp, review records and land

Status: done
Started: 2026-11-07
Done: 2026-11-07
Spec-Clarity: high
Depends-On: none
Board: STORY-066

## Story

As the owner,
I want every change to reach `main` through a proven, reviewed pull request,
so that `main` only ever holds commits the full gate passed on.

## Acceptance Criteria

AC1:
**Given** the `main` branch checked out
**When** a commit or a push to `main` is attempted
**Then** the hook refuses it and names the branch-per-story workflow

AC2:
**Given** a clean tree on a feature branch
**When** `pr_gate.py check` runs
**Then** it runs the pre-push suite and writes a stamp for HEAD (passed or failed, with each check's result); a dirty or moved tree is not stamped

AC3:
**Given** a passing stamp for the commit being pushed and a clean tree
**When** the branch is pushed
**Then** pytest, the mutation gate and Playwright are skipped with a line saying so; in every other case they run

AC4:
**Given** an open PR
**When** `pr_gate.py land <pr>` runs
**Then** it refuses unless the PR head has a passing stamp and a review record covering it, then squash-merges, waits for the release run, switches to `main` and fast-forwards it

AC5:
**Given** a local merge of `main` into a branch
**When** git writes its default `Merge ...` subject
**Then** the prepare-commit-msg hook rewrites it to `chore(merge): Merge ...`

## Must NOT

- Must NOT skip the suite on a stamp for another commit, a dirty tree or a failed run
- Must NOT merge a PR whose head the gate did not prove

## Tasks / Subtasks

- [x] `scripts/dev-tools/pr_gate.py` (check, run-unless-proven, guard-branch, land) (AC: 1-4)
- [x] `scripts/hooks/prepare_merge_commit_msg.py` (AC: 5)
- [x] `.pre-commit-config.yaml` wiring + registry policies (AC: 1,3,5)
- [x] `.primer/reviews/`, PR template, CLAUDE.md workflow section (AC: 4)
- [x] Tests on real git repositories (AC: 1-5)

## Definition of Done

- [x] All acceptance criteria verified
- [x] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [x] Ruff clean (zero violations), mypy strict, tsc clean
- [x] No changes outside the story's stated scope
- [x] References section links verified

## Existing Code

- `.pre-commit-config.yaml` -- pre-push stage (pytest, mutation gate, Playwright)
- `~/.claude/scripts/pre-pr-check.sh` -- global PR gate (primer freshness, review record)

## Dev Notes

### Testing Approach

- Real git repositories in `tmp_path`; the gate's commands are replaced by `true` / `false`.

## References

- srv02chambly `alphaseeker/scripts/dev-tools/_pr_gate_stamp.py`, `github_manager.py land`
- ADR-032
