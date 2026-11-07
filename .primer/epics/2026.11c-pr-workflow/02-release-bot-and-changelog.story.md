# Story 2026.11c.02: Release bot, changelog and dependency audit

Status: backlog
Spec-Clarity: high
Depends-On: 01
Board: STORY-067

## Story

As the owner,
I want a release to mark a delivered epic, with a short changelog,
so that versions mean something and nobody hand-bumps them.

## Acceptance Criteria

AC1:
**Given** a squash merge to `main`
**When** it flips an `epic.md` to complete, or the PR carries the `release` label
**Then** the release workflow bumps the version (minor for an epic, patch for a label) in pyproject.toml, web/package.json and uv.lock, rolls the changelog, commits, tags `vX.Y.Z` and publishes a GitHub release

AC2:
**Given** any other merge
**When** the workflow runs
**Then** it decides "no release" and ends

AC3:
**Given** CHANGELOG.md
**When** the test suite runs
**Then** it validates the file against the primer contract (one line per entry, at most 160 characters)

AC4:
**Given** a Monday
**When** the scheduled audit runs
**Then** uv.lock and web/package-lock.json are audited for known vulnerabilities

## Must NOT

- Must NOT release on a merge that edits an epic already complete
- Must NOT gate pushes or PRs from GitHub Actions

## Tasks / Subtasks

- [ ] Vendored `scripts/dev-tools/primer_changelog.py` + CHANGELOG.md (AC: 3)
- [ ] `scripts/dev-tools/release_gate.py` (decide, bump) (AC: 1,2)
- [ ] `.github/workflows/release.yml`, `dependency-audit.yml` (AC: 1,2,4)
- [ ] Tests (AC: 1-3)

## Definition of Done

- [ ] All acceptance criteria verified
- [ ] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [ ] Ruff clean (zero violations), mypy strict, tsc clean
- [ ] No changes outside the story's stated scope
- [ ] References section links verified

## References

- srv02chambly `alphaseeker/scripts/dev-tools/release_gate.py`, `.github/workflows/version-bump.yml`
- `~/.claude/skills/primer/reference/changelog.md`
- ADR-032
