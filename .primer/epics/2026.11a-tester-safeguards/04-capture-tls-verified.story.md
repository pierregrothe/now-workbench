# Story 2026.11a.04: Capture verifies instance TLS certificates

Status: done
Done: 2026-11-07
Started: 2026-11-07
Spec-Clarity: high
Depends-On: none
Board: STORY-057

## Story

As the workbench owner,
I want screenshot and video capture to refuse an invalid TLS certificate,
so that a forged or intercepted instance cannot feed fake pages into proofs or receive the instance password.

## Acceptance Criteria

AC1:
**Given** the capture and playbook drivers
**When** they launch Chromium
**Then** `--ignore-certificate-errors` is not passed

AC2:
**Given** an instance with an invalid certificate
**When** a capture runs
**Then** it fails with an error naming the certificate problem, and no proof is stored

AC3:
**Given** a valid instance
**When** a capture runs
**Then** behaviour is unchanged

## Must NOT

- Must NOT add a per-instance opt-out (owner decision 2026-11-07)
- Must NOT weaken TLS anywhere else

## Tasks / Subtasks

- [x] Remove the flag from chrome_capture.mjs and playbook_runner.mjs (AC: 1)
- [x] Map Chromium's certificate error to a clear capture failure (AC: 2)
- [x] Guard test: no `ignore-certificate-errors` anywhere in scripts/ or src/ (AC: 1)
- [x] Test the failure path: helper messages under Node, plus a manual run of the real driver against a self-signed HTTPS server (refused, no file) and example.com (captured) (AC: 2, 3)

## Definition of Done

- [x] All acceptance criteria verified
- [x] Tests added or updated and passing (pytest 100% coverage; Playwright where UI changes)
- [x] Ruff clean (zero violations), mypy strict, tsc clean
- [x] No changes outside the story's stated scope
- [x] References section links verified

## Existing Code

- `scripts/dev-tools/chrome_capture.mjs:527`, `playbook_runner.mjs:536` -- pass the flag
- `src/now_workbench/domains/capture/` -- runs the drivers

## Dev Notes

### Modules Affected

- scripts/dev-tools/chrome_capture.mjs
- scripts/dev-tools/playbook_runner.mjs
- src/now_workbench/domains/capture/

### Testing Approach

- Architecture guard test scanning for the flag
- Capture service test with a driver result carrying a certificate error

### Conventions

- No mocks: in-memory fakes, `httpx.MockTransport`, `monkeypatch.setattr` of functions (project precedent).
- Mutation-gated modules (`[tool.mutmut]`) must keep every mutant killed (ADR-029).
- Web: CSS in a sibling `*-styles.ts`, store through `StoreController` (ADR-024); phone rules at `(max-width: 768px), (max-height: 500px)` (ADR-030).

## References

- ADR: `.primer/adr/ADR-009-declarative-demo-playbooks-and-shadow-dom-automation.md` (capture and playbook drivers)
- Known issue: capture scripts launch Chromium with --ignore-certificate-errors
- Source: owner backlog review 2026-11-07 (active.md Next Steps / Known Issues)
