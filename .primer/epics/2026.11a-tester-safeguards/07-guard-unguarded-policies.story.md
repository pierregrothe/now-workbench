# Story 2026.11a.07: Mechanical checks for the three unguarded policies

Status: done
Done: 2026-11-07
Started: 2026-11-07
Spec-Clarity: medium
Depends-On: none
Board: STORY-060

## Story

As the workbench owner,
I want the otto-copilot, demo-bundles and sqlite-persistence policies to be checked by tests,
so that they are enforced, not only described in CLAUDE.md.

## Acceptance Criteria

AC1:
**Given** each policy
**When** its rule is broken in a test fixture
**Then** a guard test fails naming the policy

AC2:
**Given** the registry
**When** the story is done
**Then** the three policies are `enforced` with a check, and primer-reconcile passes

## Must NOT

- Must NOT add a new pre-commit hook when a pytest guard suffices
- Must NOT weaken an existing policy

## Tasks / Subtasks

- [x] Define one checkable rule per policy: the anthropic SDK only in interfaces/ai/{agent,client}.py; SQL only in repositories and platform/db, file databases in WAL; every shipped bundle manifest validates against DemoManifest (AC: 1)
- [x] Write the guard tests (AC: 1)
- [x] Update registry.yaml and governance tables (AC: 2)

## Definition of Done

- [x] All acceptance criteria verified
- [x] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [x] Ruff clean (zero violations), mypy strict, tsc clean
- [x] No changes outside the story's stated scope
- [x] References section links verified

## Existing Code

- `.primer/policies/registry.yaml` -- three `unguarded` entries
- `tests/test_telemetry.py` -- guard-test pattern

## Dev Notes

### Modules Affected

- tests/test_policy_guards.py (new)
- .primer/policies/registry.yaml
- .primer/governance.md

### Testing Approach

- AST/regex guards over src/ like the telemetry guards

### Conventions

- No mocks: in-memory fakes, `httpx.MockTransport`, `monkeypatch.setattr` of functions (project precedent).
- Mutation-gated modules (`[tool.mutmut]`) must keep every mutant killed (ADR-029).
- Web: CSS in a sibling `*-styles.ts`, store through `StoreController` (ADR-024); phone rules at `(max-width: 768px), (max-height: 500px)` (ADR-030).

## References

- ADR: `.primer/adr/ADR-005-constitutional-governance-and-3-tier-enforcement.md`
- Source: owner backlog review 2026-11-07 (active.md Next Steps / Known Issues)
