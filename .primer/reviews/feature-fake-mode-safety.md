# Review record -- feature/fake-mode-safety

- Head: fdcb6b9a234735d13f0dcf89630abf96d780a148
- Branch: `feature/fake-mode-safety`
- Date: 2026-11-07
- Scope: EPIC-021 story 01. `is_simulated` is exported from `now_workbench.domains.instances` and applied by the seed, property, runbook and plugin engines themselves, so callers cannot forget it. The deploy and seed APIs and the CLI paths honour it too, and a simulated instance never receives a real SDK deploy, seed call, plugin query or capture.
- Process: top-tier implementer (red first, 11 failing tests before the fix); one Sonnet adversarial review and two verify rounds.
  - Round 1: the in-scope fixes were sound, and 3 MAJOR remained.
    - `POST /deploy` deployed to a simulated instance.
    - `POST /reset` sent live DELETEs.
    - The CLI seed, rollback, reset and capture commands passed only `--fake`.
    - Also: a dead `settings.fake_mode` read, cards that overclaimed, and tautological tests.
  - Round 2 (fd6be6a) fixed them at the root:
    - `SeedEngine` applies the rule per call, the deploy endpoint simulates, and CLI capture uses the predicate;
    - the dead read is gone and the cards are corrected;
    - the tests run the real failure mapping and refuse network through a guarded httpx client.
  - Verify: one MAJOR. `/deploy` ignored the `sdk_fake_mode` preference for a real instance.
  - Round 3 (a139993) fixed it, red first. Verified.

## Verified

- 1,216 tests pass at 100% coverage.
- The reviewer reproduced every finding before its fix and checked each fix after.
- No real instance is treated as simulated: `https://fake...` is not matched.

## Not done (follow-ups)

- With `sdk_fake_mode` on, a seed or rollback against a real instance is simulated without saying so in the response. It follows AC3 ("never less"); a later UX story should state it.
