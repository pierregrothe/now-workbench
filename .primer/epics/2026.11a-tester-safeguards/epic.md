# Epic: Tester safeguards and hardening

Phase: 2026.11a
Date: 2026-11-07
Source: owner backlog review 2026-11-07 (.primer/active.md Next Steps and Known Issues)
Board: EPIC-017
Progress: 7/7 stories done -- COMPLETE

## Goal

Cap what outside testers can spend, close the remaining security gaps (CLI IDs, capture TLS), and make the no-fake-data and policy rules mechanically enforced.

## Requirements Inventory

### Functional Requirements

- FR1: Monthly billable-token allowance enforced before every Claude call
- FR2: Admin settings for allowances, own-use visible to everyone
- FR3: CLI bundle-ID path guard
- FR4: Capture verifies TLS
- FR5: No fabricated offline data (ADR-013 audit)
- FR6: Follow-ups carry earlier tool use
- FR7: Guards for three unguarded policies

### Non-Functional Requirements

- NFR1: 100% Python coverage, Playwright for UI behaviour, mutation gate stays green [Source: governance.md]
- NFR2: no fabricated data; refused or unknown values are shown as such [Source: ADR-013]

### Constraints

- C1: no new runtime dependency without an ADR [Source: stack.md]
- C2: no destructive action on a ServiceNow instance without the owner's go-ahead [Source: owner instruction]

## Coverage Map

| Requirement | Story | Status |
|-------------|-------|--------|
| FR1 | 01-usage-caps-enforced | done |
| FR2 | 02-usage-allowance-settings | done |
| FR3 | 03-cli-bundle-id-guard | done |
| FR4 | 04-capture-tls-verified | done |
| FR5 | 05-no-fabricated-fallbacks | done |
| FR6 | 06-otto-remembers-tool-use | done |
| FR7 | 07-guard-unguarded-policies | done |

## Story List

| # | Title | Dependencies | Status |
|---|-------|--------------|--------|
| 01 | Monthly Claude usage allowance per person, enforced | none | done |
| 02 | Admin settings for usage allowances | 2026.11a.01 | done |
| 03 | CLI rejects bundle IDs that escape the bundles folder | none | done |
| 04 | Capture verifies instance TLS certificates | none | done |
| 05 | ADR-013 audit: no component shows made-up data when offline | none | done |
| 06 | Otto's follow-ups know what tools he used | none | done |
| 07 | Mechanical checks for the three unguarded policies | none | done |

## Out of Scope

- Per-day allowances (owner chose monthly)
- A per-instance TLS opt-out (owner chose verify always)
