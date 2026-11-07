# Story 2026.11a.02: Admin settings for usage allowances

Status: backlog
Spec-Clarity: high
Depends-On: 2026.11a.01
Board: STORY-055

## Story

As an administrator,
I want to set the default monthly allowance and per-person overrides, and see each person's use this month,
so that I can grant testers what they need and spot heavy use.

## Acceptance Criteria

AC1:
**Given** an administrator on Settings > Conversation limits
**When** they set the default monthly allowance and save
**Then** the value persists and applies to everyone without an override

AC2:
**Given** an administrator on Settings > Team
**When** they set an override for one person
**Then** that person's allowance changes and the list shows used / allowance / percent this month

AC3:
**Given** a consultant
**When** they call the allowance API or open the section
**Then** they get 403 for others' figures but see their own use and allowance

AC4:
**Given** a phone-sized screen
**When** the section is shown
**Then** it fits without sideways scrolling (ADR-030)

## Must NOT

- Must NOT let a consultant change any allowance
- Must NOT show a number the server did not compute

## Tasks / Subtasks

- [ ] Schema migration: default allowance setting and per-person overrides (AC: 1,2)
- [ ] API endpoints (admin write, self read) (AC: 1,2,3)
- [ ] Settings UI in Conversation limits and Team, with own-use line for everyone (AC: 1,2,4)
- [ ] Otto action `set_usage_allowance` (admin, confirm in words) (AC: 1,2)
- [ ] Tests: API, Playwright desktop + phone (AC: 1-4)

## Definition of Done

- [ ] All acceptance criteria verified
- [ ] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [ ] Ruff clean (zero violations), mypy strict, tsc clean
- [ ] No changes outside the story's stated scope
- [ ] References section links verified

## Existing Code

- `web/src/views/now-limits-settings.ts`, `now-team-settings.ts`
- `src/now_workbench/domains/identity` `require_admin`

## Dev Notes

### Modules Affected

- src/now_workbench/platform/db/schema.py (v14)
- src/now_workbench/domains/settings/
- src/now_workbench/interfaces/api/settings_api.py
- web/src/views/now-limits-settings.ts, now-team-settings.ts

### Testing Approach

- pytest API tests with admin and consultant users
- Playwright: set override, see percentage; phone fit

### Conventions

- No mocks: in-memory fakes, `httpx.MockTransport`, `monkeypatch.setattr` of functions (project precedent).
- Mutation-gated modules (`[tool.mutmut]`) must keep every mutant killed (ADR-029).
- Web: CSS in a sibling `*-styles.ts`, store through `StoreController` (ADR-024); phone rules at `(max-width: 768px), (max-height: 500px)` (ADR-030).

## References

- ADR: `.primer/adr/ADR-031-monthly-usage-allowances.md`
- ADR: `.primer/adr/ADR-020-impersonation.md` (impersonation)
- Source: owner backlog review 2026-11-07 (active.md Next Steps / Known Issues)
