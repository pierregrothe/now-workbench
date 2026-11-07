# Review record -- feature/domain-card-checks

- Head: f028207d4b4b56e14640d134effc3827f77aadd2
- Branch: `feature/domain-card-checks`
- Date: 2026-11-07
- Scope: EPIC-020 stories 01-02 (ADR-033):
  - `card-dead-references` ratchet (baseline 0, in ratchet-all);
  - the `domain-card-freshness` pre-push nudge (advisory);
  - registry and governance rows, and ADR-032's repository-settings section.
- Process: top-tier implementer; one Sonnet adversarial review and two verify rounds.
  - Round 1: 5 MAJOR.
    - Call-shaped spans escaped.
    - `platform` and `profile` were skipped as stdlib names.
    - Dotted names were checked per part, so about 99.7% of wrong `Class.method` pairs passed.
    - Honest names were flagged (`__init__`, DDL tables, `WORKBENCH_*` settings).
    - The nudge could crash on a staged card.
  - Round 2 (f9e2ef0, 94b73d4) fixed all five:
    - member-aware `Index.resolves`, with inherited members;
    - leading-identifier extraction, doubled backticks and `~~~` fences;
    - the project-module exception, DDL and env names, and a crash-proof nudge.
  - Verify: 1 MAJOR, `platform/config` has no `__init__.py`, so 97 of 6,512 honest dotted paths failed. 2 MINOR: module-named variables were too permissive, and `router.get` is flagged.
  - Round 3 (this head): every folder on a path is linked to its parent. A module-named variable's member must be that module's or some class's attribute.

## Verified

- 14 tests pass.
- The 19 drafted cards (story 03, not in this PR): 676 references, 0 dead, on this head.
- The verifier ran dead_references() end to end on a scratch tree for every fixed case.

## Not done (follow-ups)

- 129 of 192 classes stay open (external bases: pydantic, enums, exceptions), so their members are not checked. Repositories are closed.
- Not extracted: `Foo | None`, `a, b`, a span wrapped across lines. An unclosed fence hides the rest of the card.
- `router.get`-style decorator names need an allowlist entry if a card uses them.
