# Epic: Otto memory per person

Phase: 2026.11f
Date: 2026-11-07
Source: PRD-004 (accepted 2026-11-07), ADR-034
Board: EPIC-022
Progress: 0/3 stories done

## Goal

Otto remembers each person's preferences, work context and ServiceNow focus across
conversations; the person sees and controls it; nobody else does.

## Requirements Inventory

### Functional Requirements

- FR1: Owner-scoped memory storage, API and Profile > Memory (list, edit, hide, delete, delete all, on/off)
- FR2: Background extraction with Haiku 5.5 after 10 quiet minutes, capped, secret-filtered, counted in the allowance
- FR3: Recall frozen per thread (cache-safe), computed most-used ServiceNow areas, and the remember / forget / my_memory tools

### Non-Functional Requirements

- NFR1: Tests never call the Claude API (fake client) [Source: CLAUDE.md]
- NFR2: Owner-only visibility; "view as" acts as the viewed person [Source: PRD-004, ADR-020]

### Constraints

- C1: The anthropic SDK stays in interfaces/ai (policy guard) [Source: tests/test_policy_guards.py]
- C2: Schema version follows the feedback row's (EPIC-018 story 01) [Source: ADR-034]

## Coverage Map

| Requirement | Story | Status |
|-------------|-------|--------|
| FR1 | 01-memory-store-and-profile | backlog |
| FR2 | 02-memory-extraction | backlog |
| FR3 | 03-memory-recall-and-tools | backlog |

## Story List

| # | Title | Dependencies | Status |
|---|-------|--------------|--------|
| 01 | Memory store, API and Profile > Memory | EPIC-018/01 landed | backlog |
| 02 | Background extraction | 01 | backlog |
| 03 | Recall, computed areas and Otto's memory tools | 01 | backlog |

## Out of Scope

- See PRD-004 Out of Scope (no sharing, no admin view, no embeddings, no attachments, no secrets)
