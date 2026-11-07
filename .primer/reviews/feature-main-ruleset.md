# Review record -- feature/main-ruleset

- Head: 289af5ec5288a5780300131f13e8979e5e46cfa1
- Branch: `feature/main-ruleset`
- Date: 2026-11-07
- Scope: main is protected by a GitHub ruleset (PRs only, squash, linear history, no force push or deletion, no bypass). The release bot therefore lands its bump as its own `release/vX` PR and tags the merge commit. Also fixes the changelog-roll test that broke once v2026.11.0 existed.
- Process: top-tier implementer; one Sonnet adversarial review and two verify rounds.
  - Round 1: 2 MAJOR, 5 MINOR. A failed run left a branch and PR that blocked every later release. A rerun could double-bump. The notes could be cut from the wrong tree after gh switched branches. Minors: the retry loop, the concurrency drop, gh's local switch, substring-only tests, the changelog entry.
  - Round 2 (2a343bd): re-entrant PR step, second-release guard, notes cut before the merge, a merge-commit poll, YAML-parsed tests with bash -n per step. Verified, with 2 MINOR: a transient gh error ended the poll, and the guard relied on the squash body.
  - Round 3 (289af5e): the poll tolerates errors, and the guard marker is in the subject ("chore(release): vX for PR #N"), with grep tests for #5 against #50.

## Verified

- 74 workflow tests pass. The ruleset is active on GitHub (id 26760163) and the API lists its four rules and no bypass actors.
- The reviewer extracted the release-notes awk from the parsed YAML and ran it against a rolled changelog: 138 bytes, identical to the old extraction.

## Not done (follow-ups)

- The owner must enable "Allow GitHub Actions to create and approve pull requests". Without it the next release fails at `gh pr create`.
- MINOR-5 (a governance line in CHANGELOG.md) is kept; the owner reads the changelog too.
- The new bump-through-PR path runs for the first time at the next epic close.
