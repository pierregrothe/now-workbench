## Summary

<!-- What changed and why, in a few lines. The story file holds the detail. -->

Story: `.primer/epics/<epic>/<NN-slug>.story.md`

## Gate

- [ ] `python scripts/dev-tools/pr_gate.py check` passed on the head (stamp recorded)
- [ ] Review record `.primer/reviews/<branch-with-dashes>.md` names the reviewed `Head:`
- [ ] One `CHANGELOG.md` line under `[Unreleased]` for a user-visible change (none for internal work)
- [ ] Primer synced (story status, epic progress)

## Testing

<!-- What was run beyond the gate: manual checks, a live instance, screenshots. -->

## Deployment notes

<!-- Schema migrations, new settings or .env keys, anything srv01chambly needs. -->
