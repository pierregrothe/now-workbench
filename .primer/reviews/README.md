# Review records

One file per branch: `<branch-with-slashes-as-dashes>.md` (e.g. `feature-pr-workflow.md`).

Because this folder exists, the global `pre-pr-check.sh` hook blocks `gh pr create` on a branch
that touches `src/` until the branch's record carries `Head: <sha>`, the last commit outside
`.primer/reviews/`, `active.md` and `progress.md`. `pr_gate.py land` checks it again (ADR-032).

Write the record before `pr_gate.py check`, so the stamp covers the commit that holds it.

```markdown
# Review record -- feature/<slug>

- Head: <full sha of the reviewed commit>
- Branch: `feature/<slug>`
- Date: YYYY-MM-DD
- Scope: what the branch changes
- Process: who reviewed, and the rounds (findings and what was fixed)

## Verified

## Not done (follow-ups)
```
