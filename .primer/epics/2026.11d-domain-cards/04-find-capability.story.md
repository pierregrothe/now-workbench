# Story 2026.11d.04: Capability search, lexical and Jev-backed

Status: backlog
Spec-Clarity: high
Depends-On: none
Board: STORY-071

## Story

As an agent about to write a helper,
I want to ask whether it already exists,
so that I reuse it instead of duplicating it.

## Acceptance Criteria

AC1:
**Given** a plain-words query
**When** `find_capability.py <words>` runs
**Then** it ranks public symbols of `src/now_workbench` (each domain's `__all__` and public defs, with their first docstring line) by word overlap and prints name, location and summary

AC2:
**Given** `--semantic` and `TYPESAFE_API_KEY` set
**When** the search runs
**Then** each candidate becomes one Jev noul question and results are ranked by probability

AC3:
**Given** `--semantic` with no key, or a failed call
**When** the search runs
**Then** it prints `[SEMANTIC] not run -- <reason>` and keeps the lexical results

## Must NOT

- Must NOT call the Jev API from the test suite
- Must NOT present lexical results as semantic ones

## Tasks / Subtasks

- [ ] `scripts/dev-tools/find_capability.py` + Jev client (AC: 1-3)
- [ ] CLAUDE.md line (AC: 1)
- [ ] Tests with a fake transport (AC: 1-3)

## Definition of Done

- [ ] All acceptance criteria verified
- [ ] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [ ] Ruff clean (zero violations), mypy strict, tsc clean
- [ ] No changes outside the story's stated scope
- [ ] References section links verified

## References

- srv02chambly `alphaseeker/scripts/dev-tools/find_capability.py`, `.ratchet/_jev.py`
- typesafe plugin skill
- ADR-033
