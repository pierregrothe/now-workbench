# Review record -- feature/domain-cards

- Head: 26b4dedd08c70e461f7b1f47610780ee2767a63a
- Branch: `feature/domain-cards`
- Date: 2026-11-07
- Scope: EPIC-020 story 03, a `CLAUDE.md` card in each of the 19 domains under `src/now_workbench/domains/` (ADR-033). Documentation only; no code changes.
- Process: four top-tier agents wrote the cards (alphaseeker's journal card as the exemplar). Four independent Sonnet fact-checkers then checked every claim against the code, and three Sonnet editors applied the corrections after confirming each one in src.
  - Fact-check: about 60 corrections, none skipped. These included:
    - wrong statements: `workspace_dir` said to ignore its env variable (false, the checker ran it); a value with an inner quote said not to be read (it is cut at the quote); the wrong ADR number (013 for 028); a CLI command name (`instantiate` for `generate`);
    - overstated invariants: owner filters, "never fatal", "always writes the audit row first";
    - non-public names listed under "do not reinvent": `snapshot_bundle`, `detect_media_type`, `_query_plugin_active`;
    - wrong caller lists (properties callers inside or outside the session; replies.py missing from sharing);
    - lines that restated the root CLAUDE.md, now removed.

## Verified

- `card-dead-references`: 0 dead over 19 cards (1,455 lines); every card is ASCII only and at most 96 lines.
- Every name in each domain's `__all__` appears in its card's entry points (checked by the fact-checkers).

## Not done (follow-ups)

- The writers and checkers found about 15 real code defects (for example, a fake:// bundle with package.json attempts a real deploy, property restore reports success after failures, capture assumes Xanadu, sync plugin queries block the async pipeline). The cards record them as gotchas; fixing them is a separate backlog epic.
- `platform/` and `interfaces/` have no cards yet (out of scope).
