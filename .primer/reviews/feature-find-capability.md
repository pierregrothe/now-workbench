# Review record -- feature/find-capability

- Head: b3de9ca5f494536be7af1b277d57217fc8ca8867
- Branch: `feature/find-capability`
- Date: 2026-11-07
- Scope: EPIC-020 story 04 (ADR-033), `scripts/dev-tools/find_capability.py`:
  - an index of public module-level symbols, with domain exports tagged;
  - lexical ranking that weights rare words and doubles name matches;
  - a `--semantic` TypeSafe Jev pass, ranked and never thresholded, that says "not run" instead of guessing.
  - Also the CLAUDE.md command and the epic close.
- Process: top-tier implementer; one Sonnet adversarial review (its probes used MockTransport only, with no network).
  - Round 1: 3 MAJOR.
    - Odd 200 bodies raised a traceback instead of reading as "not run".
    - Fifteen interface route handlers were tagged export.
    - Untested paths: later-chunk failure, retries, weighting, the async index, the limit.
  - Minors: `-es` plurals, `get`/`set` as stop words, annotated `__all__`, NaN and out-of-range probabilities, the cost claim, a sleep after the last retry, `--limit` bounds.
  - Round 2 (this head) fixed all of them. Deliberately left: "statuses" still stems as "statuse"; methods, constants and aliases are not indexed; `Retry-After` is ignored.

## Verified

- 36 tests pass, all with `httpx.MockTransport`; the suite never calls Jev.
- One live query, with the owner's go-ahead ("Go", 2026-11-07), on `jev-1.13.0`: "path that cannot escape its folder" ranked `safe_child` first (0.32). That is the exact match the lexical pass misses.

## Not done (follow-ups)

- A gold set of queries to measure recall, as alphaseeker did, before relying on the semantic rank.
