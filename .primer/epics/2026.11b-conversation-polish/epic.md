# Epic: Conversation polish and housekeeping

Phase: 2026.11b
Date: 2026-11-07
Source: owner backlog review 2026-11-07 (.primer/active.md Next Steps and Known Issues)
Board: EPIC-018
Progress: 1/5 stories done

## Goal

Finish PRD-002 (feedback row, Otto look on four screens), make demo-app removal a confirmed action, and mirror the code layout in tests.

## Requirements Inventory

### Functional Requirements

- FR1: Reply feedback stored and listed
- FR2: Synthesizer and Capture restyle
- FR3: Fluent and Artifact cards restyle
- FR4: Confirmed demo-app removal
- FR5: Tests mirror layout

### Non-Functional Requirements

- NFR1: 100% Python coverage, Playwright for UI behaviour, mutation gate stays green [Source: governance.md]
- NFR2: no fabricated data; refused or unknown values are shown as such [Source: ADR-013]

### Constraints

- C1: no new runtime dependency without an ADR [Source: stack.md]
- C2: no destructive action on a ServiceNow instance without the owner's go-ahead [Source: owner instruction]

## Coverage Map

| Requirement | Story | Status |
|-------------|-------|--------|
| FR1 | 01-chat-feedback-row | done |
| FR2 | 02-restyle-synthesizer-capture | backlog |
| FR3 | 03-restyle-fluent-artifacts | backlog |
| FR4 | 04-remove-deployed-demo-app | backlog |
| FR5 | 05-tests-mirror-layout | backlog |

## Story List

| # | Title | Dependencies | Status |
|---|-------|--------------|--------|
| 01 | Thumbs up/down and Get help under Otto's replies | none | done |
| 02 | Synthesizer and Media Capture in the Otto look | none | backlog |
| 03 | Fluent Explorer and Artifact library cards in the Otto look | none | backlog |
| 04 | Remove a deployed demo app from an instance | none | backlog |
| 05 | Tests mirror the platform / domains / interfaces layout | none | backlog |

## Out of Scope

- External feedback services
- Removing apps not deployed by the workbench
