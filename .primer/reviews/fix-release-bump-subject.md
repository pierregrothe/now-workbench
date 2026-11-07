# Review record -- fix/release-bump-subject

- Head: a72570586576ae8b6ab53e7a669fa8133e4935fc
- Branch: `fix/release-bump-subject`
- Date: 2026-11-07
- Scope:
  - A release is cut when a merge ships a PRD (front-matter `status: shipped`) or carries the `release` label; closing an epic no longer releases (owner, 2026-11-07).
  - The bot's bump subject becomes `chore(version): bump to vX for PR #N`, which the global PR gate exempts, and the second-release guard is updated to match.
- Process: top-tier implementer; one Sonnet adversarial review.
  - No BLOCKING or MAJOR.
  - MINOR findings: the front-matter parser failed silently on CRLF, a BOM, quoted values and comments; stale "epic closes" prose in the CHANGELOG preamble; one over-long ADR line.
  - Fixed: a tolerant parser with five new cases, and the prose and wrap. The same stale sentence in the vendored changelog engine is left, because it must stay byte-identical to the primer skill template (a dotfiles follow-up).

## Verified

- 46 release tests pass.
- The four real PRDs parse as not shipped, so `decide(HEAD)` returns no release.
- The guard regex matches `... for PR #8 (#9)` and rejects `#80`.
- `git log --grep='^chore(version): bump to'` uses BRE, where the parentheses are literal, so the hook's exemption applies.

## Not done (follow-ups)

- Update the primer skill's changelog template wording ("Releases are cut when a PRD ships") in claude-dotfiles, then reinstall it here.
