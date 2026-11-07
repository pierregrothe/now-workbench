# Story 2026.11b.04: Remove a deployed demo app from an instance

Status: backlog
Spec-Clarity: medium
Depends-On: none
Board: STORY-064

## Story

As a solution consultant,
I want to uninstall a demo app the workbench deployed, from the Artifact library or by asking Otto,
so that instances do not fill up with old demo apps.

## Acceptance Criteria

AC1:
**Given** an app the workbench deployed (recorded scope)
**When** the person asks to remove it
**Then** a confirmation requires typing the app scope, and Otto must confirm in words

AC2:
**Given** a confirmed removal on the fake instance
**When** it runs
**Then** the uninstall request is sent for that scope only and the deployment record is marked removed

AC3:
**Given** an app the workbench did not deploy
**When** removal is requested
**Then** it is refused

AC4:
**Given** the live instance (Alectri)
**When** the story is verified
**Then** the live run happens only after the owner's explicit go-ahead

## Must NOT

- Must NOT remove anything not recorded as deployed by the workbench
- Must NOT run against a live instance without the owner's go-ahead

## Tasks / Subtasks

- [ ] Find the supported uninstall path (SDK or API) and record it in the story (AC: 2)
- [ ] Domain operation + destructive action spec (AC: 1,2,3)
- [ ] UI button + Otto action (AC: 1)
- [ ] Tests on the fake instance; live check with go-ahead (AC: 2,3,4)

## Definition of Done

- [ ] All acceptance criteria verified
- [ ] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [ ] Ruff clean (zero violations), mypy strict, tsc clean
- [ ] No changes outside the story's stated scope
- [ ] References section links verified

## Existing Code

- Demo deployment pipeline `src/now_workbench/domains/demos/pipeline.py`
- Known issue: removal is manual (System Applications)

## Dev Notes

### Modules Affected

- src/now_workbench/domains/demos/
- src/now_workbench/interfaces/ai/tools/
- web/src/components/now-demo-catalog.ts

### Testing Approach

- httpx.MockTransport / fake SDK runner asserting the exact uninstall request

### Conventions

- No mocks: in-memory fakes, `httpx.MockTransport`, `monkeypatch.setattr` of functions (project precedent).
- Mutation-gated modules (`[tool.mutmut]`) must keep every mutant killed (ADR-029).
- Web: CSS in a sibling `*-styles.ts`, store through `StoreController` (ADR-024); phone rules at `(max-width: 768px), (max-height: 500px)` (ADR-030).

## References

- ADR: `.primer/adr/ADR-026-conversational-control-and-ui-parity.md` (destructive actions confirm)
- Source: owner backlog review 2026-11-07 (active.md Next Steps / Known Issues)
