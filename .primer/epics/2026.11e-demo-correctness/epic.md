# Epic: Demo correctness fixes

Phase: 2026.11e
Date: 2026-11-07
Source: defects recorded while writing the domain cards (EPIC-020, PR #4 notes)
Board: EPIC-021
Progress: 1/5 stories done

## Goal

The defects the card writers found while reading every domain are confirmed with a failing test,
then fixed: nothing simulated reaches a real instance, a restore says when it failed, captures use
the instance's real release, and the pipeline never blocks the server.

## Requirements Inventory

### Functional Requirements

- FR1: One simulated-instance rule, used everywhere; a simulated instance never triggers a real deploy
- FR2: Property apply keeps the true originals; restore reports failures and keeps the snapshot
- FR3: Capture uses the instance's detected release, never a Xanadu default
- FR4: The demo pipeline's plugin queries do not block the event loop
- FR5: Sharing and group rules: a missing version zip is a 404, versions cannot collide, the CLI delete cleans the registry, a group keeps an admin

### Non-Functional Requirements

- NFR1: Each defect is first reproduced by a failing test (red first) [Source: review practice]
- NFR2: 100% coverage and the mutation gate stay green [Source: governance.md]

### Constraints

- C1: No destructive action on a real ServiceNow instance in tests (fake mode and fakes only) [Source: owner instruction]

## Coverage Map

| Requirement | Story | Status |
|-------------|-------|--------|
| FR1 | 01-fake-mode-safety | done |
| FR2 | 02-property-snapshot-integrity | backlog |
| FR3 | 03-capture-detected-release | backlog |
| FR4 | 04-pipeline-nonblocking-plugins | backlog |
| FR5 | 05-sharing-and-group-rules | backlog |

## Story List

| # | Title | Dependencies | Status |
|---|-------|--------------|--------|
| 01 | One simulated-instance rule; no real deploy from fake mode | none | done |
| 02 | Property snapshots keep the originals; restore reports failure | none | backlog |
| 03 | Capture uses the detected release | none | backlog |
| 04 | Plugin queries off the event loop | none | backlog |
| 05 | Sharing and group rules hold | none | backlog |

## Out of Scope

- Runbook parser and Fluent parser gaps (logged in the cards; a later epic)
- Hygiene items (missing headers and __all__) unless a story touches the file
