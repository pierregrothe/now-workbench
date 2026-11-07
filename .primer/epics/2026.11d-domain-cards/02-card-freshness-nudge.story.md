# Story 2026.11d.02: Advisory freshness nudge for domain cards

Status: done
Started: 2026-11-07
Done: 2026-11-07
Spec-Clarity: high
Depends-On: none
Board: STORY-069

## Story

As the owner,
I want to hear when a domain moved on but its card did not,
so that cards get refreshed before they mislead.

## Acceptance Criteria

AC1:
**Given** a tracked card
**When** the branch is pushed
**Then** the hook counts commits touching the domain's `*.py` since the card's last commit and its age, and names the card when either passes 15 commits or 90 days

AC2:
**Given** any result
**When** the hook ends
**Then** it exits 0 (advisory, never blocks)

## Must NOT

- Must NOT block a push

## Tasks / Subtasks

- [x] `scripts/hooks/check_domain_card_freshness.py` (AC: 1,2)
- [x] pre-push hook + registry policy (AC: 2)
- [x] Tests on a real git repository (AC: 1,2)

## Definition of Done

- [x] All acceptance criteria verified
- [x] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [x] Ruff clean (zero violations), mypy strict, tsc clean
- [x] No changes outside the story's stated scope
- [x] References section links verified

## References

- srv02chambly `alphaseeker/scripts/hooks/check_domain_card_freshness.py`
- ADR-033
