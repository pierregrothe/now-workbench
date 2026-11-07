# Review record -- feature/pr-workflow

- Head: aac912abaed84cf7342c18d38f3e6c2da6f417c2
- Branch: `feature/pr-workflow`
- Date: 2026-11-07
- Scope: EPIC-019 (ADR-032), the branch-and-PR workflow ported from srv02chambly alphaseeker:
  - branch guards (guard-branch at pre-commit and pre-merge-commit, guard-push), merge-subject hook;
  - `pr_gate.py` check (stamp per commit), run-unless-proven (pre-push skip), land;
  - review records, PR template; release bot (`release_gate.py`, release.yml), CalVer;
  - vendored primer changelog engine, condensed CHANGELOG.md, weekly dependency audit.
- Process: top-tier implementer; one Sonnet adversarial review, then a verify review.
  - Round 1: 3 MAJOR, 6 MINOR. Multi-ref pushes are seen only by their first ref. A record naming a commit already on main covered any branch. The tag and main pushes were not atomic. Minors: a clean merge on main, an unset TO_REF, clock skew, a parentless decide, a label starting with `-`, tests that could not tell a run from a skip.
  - Round 2 (aac912a) fixed every one except the first-ref limit, which is documented in ADR-032 (pre-commit exposes only that ref).
  - Verify review: verified, no BLOCKING or MAJOR.

## Verified

- 58 tests on real git repositories (fake `gh` script): stamp pass/fail, skip only for the stamped pushed HEAD (marker file proves run vs skip), record ancestry and main-tip refusal, land refusals and happy path, release decision, CalVer bump, changelog roll and validate.
- `uv audit` and `npm audit` clean locally; the release-notes awk extraction was tested by the reviewer.

## Not done (follow-ups)

- GitHub branch protection on `main` (repository setting, the owner's call) is the only complete guard against multi-ref pushes and `--no-verify`.
- The release workflow and `land`'s wait run for the first time on this PR's merge.
