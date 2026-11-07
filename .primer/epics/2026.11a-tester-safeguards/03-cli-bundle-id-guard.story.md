# Story 2026.11a.03: CLI rejects bundle IDs that escape the bundles folder

Status: done
Done: 2026-11-07
Started: 2026-11-07
Spec-Clarity: high
Depends-On: none
Board: STORY-056

## Story

As the workbench owner,
I want every `workbench` command that takes a bundle or template ID to apply the same ID check as the API,
so that a crafted ID such as `../../etc` can never read or write outside the bundles folder.

## Acceptance Criteria

AC1:
**Given** any CLI command taking a bundle ID (demo inspect/clone/runbook/verify/seed, fluent schema/diff)
**When** it is given `../x`, `a/b`, an absolute path or an empty string
**Then** it exits with code 2 and a clear message, touching no file

AC2:
**Given** a valid ID
**When** the command runs
**Then** behaviour is unchanged

## Must NOT

- Must NOT duplicate the ID rule: reuse the API's validator
- Must NOT change command names or options

## Tasks / Subtasks

- [x] Find the API's bundle-id validator (`safe_child` in platform/config/paths.py) and expose its rule as `check_name` (AC: 1)
- [x] Typer callback applying it to every bundle-ID argument (AC: 1,2)
- [x] Parametrised CLI tests per command and per bad ID (AC: 1,2)

## Definition of Done

- [x] All acceptance criteria verified
- [x] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [x] Ruff clean (zero violations), mypy strict, tsc clean
- [x] No changes outside the story's stated scope
- [x] References section links verified

## Existing Code

- `src/now_workbench/interfaces/cli/bundles.py`, `fluent.py` -- unvalidated `typer.Argument` IDs
- `tests/test_api_bundle_id_safety.py` -- the API-side rule

## Dev Notes

### Modules Affected

- src/now_workbench/interfaces/cli/{bundles,fluent}.py
- src/now_workbench/domains/bundles/__init__.py

### Testing Approach

- CliRunner parametrised over commands x bad IDs; assert exit 2 and no filesystem change (tmp bundles dir)

### Conventions

- No mocks: in-memory fakes, `httpx.MockTransport`, `monkeypatch.setattr` of functions (project precedent).
- Mutation-gated modules (`[tool.mutmut]`) must keep every mutant killed (ADR-029).
- Web: CSS in a sibling `*-styles.ts`, store through `StoreController` (ADR-024); phone rules at `(max-width: 768px), (max-height: 500px)` (ADR-030).

## References

- ADR: `.primer/adr/ADR-015-domain-oriented-package-architecture.md`
- Known issue: CLI bundle-id arguments are not path-guarded
- Source: owner backlog review 2026-11-07 (active.md Next Steps / Known Issues)
