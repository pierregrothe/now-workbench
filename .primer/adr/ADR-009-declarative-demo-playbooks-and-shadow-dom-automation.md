# ADR-009: Declarative Demo Playbooks, Native Shadow-DOM Automation, and Storage State Session Persistence

**Status:** accepted
**Date:** 2026-10-30

## Context

Demonstrations in ServiceNow require authentic live execution proof: logging into the instance,
navigating Polaris workspaces, clicking target records, and filling form inputs. The early capture
engine relied on ad-hoc scripts that captured single screenshots and synthesized video frames on a canvas,
lacking real multi-step execution proof. Furthermore, ServiceNow's Next Experience (Polaris) relies heavily
on deeply nested Custom Elements and Shadow DOM structures, where traditional selector traversal fails.

## Decision

1. **Declarative Playbook Specification (`walkthrough/playbook.json`)**:
   - Every demo bundle defines an executable sequence of steps (navigate, impersonate, move_and_click,
     type, wait_for_selector, assert_text) alongside `guide.md`.
2. **Native Shadow-DOM Piercing Automation**:
   - Adopt an async browser driver that traverses open Shadow DOM trees natively using modern
     locators (`page.locator(...)`), supporting both legacy `iframe` forms and Next Experience web components.
3. **Session State Persistence (`storage_state`)**:
   - Authenticate once against `/login.do`, verify session cookies, and persist authenticated state
     per instance (`<data_dir>/sessions/<instance_id>.json`). Subsequent demonstration runs reuse the
     authenticated session without repetitive login friction.
4. **Native Context Video Proof Recording (`record_video_dir`)**:
   - Record actual browser execution directly at the browser context level into VP8 WebM video files,
     accompanied by an execution audit trail (`step_results`, `timestamps`, `live_authenticated: bool`).

## Consequences

- Automated proof videos show real DOM navigation, visible cursor movements, and live field mutations.
- Demo playbooks are portable, version-controlled JSON artifacts packaged inside `.sn-demo.zip`.
- Offline preview mode falls back to simulated workspace layouts with zero network calls for automated tests.
