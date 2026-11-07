# ADR-033: Domain Cards and Capability Search

**Status:** accepted 2026-11-07
**Date:** 2026-11-07
**Builds on:** ADR-015 (domain packages), ADR-032 (PR workflow)
**Epic:** `.primer/epics/2026.11d-domain-cards/epic.md`

## Context

The owner's other project (alphaseeker, srv02chambly) keeps a short `CLAUDE.md` card in each
domain. Claude Code loads it when working in that directory, so an agent learns the
domain's entry points, wiring and traps without reading every module. Two offline checks keep the
cards honest, and a "does this already exist?" search, optionally backed by the TypeSafe
Jev model, stops agents writing duplicate helpers. The owner asked for the same here
(2026-11-07). The cards themselves are written and reviewed by hand; Jev is used only by the
search.

## Decision

- **Cards:** `src/now_workbench/domains/<name>/CLAUDE.md`, one format, about 70 to 100 lines. The
  sections are: what the domain does and does not do; public entry points from
  `now_workbench.domains.<name>`; wiring (repository, `db_session`, callers); invariants and
  gotchas; do not reinvent. A card states the plumbing, not the history, and does not restate
  the root CLAUDE.md.
- **Dead references (blocking):** the `card-dead-references` ratchet (baseline 0, in
  `ratchet-all`) counts backticked, code-shaped names a card gives that `src/now_workbench`
  does not define, parsed with `ast`, never imported. Real non-code names go in
  `.ratchet/card_reference_allowlist.txt` with a reason.
- **Freshness (advisory):** the `domain-card-freshness` pre-push hook names a card when its
  domain took 15 commits, or the card is 90 days old, since the card last changed.
- **Capability search (story 04):** `scripts/dev-tools/find_capability.py`, lexical by default.
  With `--semantic` it asks Jev (`TYPESAFE_API_KEY`) one yes/no question per candidate. With
  no key, or on any failed call, it says the semantic pass did not run.

## Consequences

- Cards can still be wrong in ways the ratchet cannot see (a false invariant); the review at
  write time and the freshness nudge are the only defences.
- Jev queries cost money (about $0.025 each in alphaseeker) and are made only on request, never
  from the test suite or a hook.

