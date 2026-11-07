# Story 2026.11a.05: ADR-013 audit: no component shows made-up data when offline

Status: done
Done: 2026-11-07
Started: 2026-11-07
Spec-Clarity: high
Depends-On: none
Board: STORY-058

## Story

As a solution consultant,
I want every screen to show an explicit error or empty state when the backend fails,
so that I never demo invented numbers or records.

## Acceptance Criteria

AC1:
**Given** each listed component (shell, demo catalog, presenter HUD, fluent explorer, welcome modal, console, capture prefs, profile settings)
**When** its backend request fails (Playwright route returns 500 or aborts)
**Then** it shows an error or empty state and no fabricated item, number or record

AC2:
**Given** the codebase
**When** searched for offline/fallback data literals in web/src
**Then** none remain except labelled empty states

## Must NOT

- Must NOT change behaviour when the backend answers
- Must NOT hide the error behind a retry loop

## Tasks / Subtasks

- [x] Audit each component's fallback branch; remove fabricated data (AC: 1,2)
- [x] One Playwright spec per component proving the error/empty state (AC: 1)
- [x] Update ADR-013 follow-up note to done (AC: 2)

## Definition of Done

- [x] All acceptance criteria verified
- [x] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [x] Ruff clean (zero violations), mypy strict, tsc clean
- [x] No changes outside the story's stated scope
- [x] References section links verified

## Existing Code

- ADR-013 Consequences lists the components
- `web/e2e/deepfix-*.spec.ts` -- pattern for failure-path specs

## Dev Notes

### Modules Affected

- web/src/components/{now-workbench-shell,now-demo-catalog,now-presenter-hud,now-fluent-explorer,now-welcome-modal,now-console,now-capture-prefs}.ts
- web/src/views/now-profile-settings.ts

### Outcome (2026-11-07)

- Already honest (earlier deep-fix, specs exist): demo catalog, presenter HUD, settings load/save, profile.
- Fixed: Fluent explorer bundle list (was silent) and welcome guide save (was silent, closed as if saved; now saves first and stays open with the reason).
- Accepted: the shell keeps interface defaults when preferences cannot load (no data shown from them); capture prefs' "Offline Simulation Fallback" is a setting label.
- Not rendered anywhere: `now-console` (dead code, flagged, left unchanged).

### Testing Approach

- Playwright with page.route returning 500 / abort per component

### Conventions

- No mocks: in-memory fakes, `httpx.MockTransport`, `monkeypatch.setattr` of functions (project precedent).
- Mutation-gated modules (`[tool.mutmut]`) must keep every mutant killed (ADR-029).
- Web: CSS in a sibling `*-styles.ts`, store through `StoreController` (ADR-024); phone rules at `(max-width: 768px), (max-height: 500px)` (ADR-030).

## References

- ADR: `.primer/adr/ADR-013-playwright-end-to-end-ui-testing.md`
- Source: owner backlog review 2026-11-07 (active.md Next Steps / Known Issues)
