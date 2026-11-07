# Epic: Domain cards and capability search

Phase: 2026.11d
Date: 2026-11-07
Source: owner request 2026-11-07 -- port alphaseeker's domain cards (srv02chambly)
Board: EPIC-020
Progress: 3/4 stories done

## Goal

Every domain carries a short, true `CLAUDE.md` card that tells an agent how to wire into it,
the cards cannot silently point at renamed code, and an agent can ask "does this already
exist?" before writing a helper (lexically, or semantically through TypeSafe Jev).

## Requirements Inventory

### Functional Requirements

- FR1: A ratchet counts identifiers a card names that `src/now_workbench` does not define (baseline 0)
- FR2: An advisory pre-push nudge names cards whose domain moved on since the card was written
- FR3: A card for each of the 19 domains, in one format, reviewed against the code
- FR4: `find_capability.py` searches public symbols lexically, and with `--semantic` through Jev

### Non-Functional Requirements

- NFR1: The suite never calls the paid Jev API; tests use a fake transport [Source: CLAUDE.md, no mocks]
- NFR2: A missing key or a failed call says the semantic search did not run; it never fakes an answer [Source: ADR-013]

### Constraints

- C1: No new runtime dependency (httpx and pyyaml are already locked) [Source: stack.md]
- C2: Cards state the plumbing, not the history; about 70 to 100 lines each [Source: alphaseeker CK.04]

## Coverage Map

| Requirement | Story | Status |
|-------------|-------|--------|
| FR1 | 01-card-dead-reference-ratchet | done |
| FR2 | 02-card-freshness-nudge | done |
| FR3 | 03-domain-cards | done |
| FR4 | 04-find-capability | backlog |

## Story List

| # | Title | Dependencies | Status |
|---|-------|--------------|--------|
| 01 | Ratchet on dead identifiers in domain cards | none | done |
| 02 | Advisory freshness nudge for domain cards | none | done |
| 03 | A card for each of the 19 domains | 01 | done |
| 04 | Capability search, lexical and Jev-backed | none | backlog |

## Out of Scope

- alphaseeker's Jev docstring ratchets (jev-docstring-truth, jev-silent-stub) and canonical seams
- Cards for `platform/` and `interfaces/` (domains first)
