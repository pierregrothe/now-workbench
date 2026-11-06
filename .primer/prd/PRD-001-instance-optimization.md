---
id: PRD-001
title: Instance Optimization
status: draft
date: 2026-11-06
adrs: [ADR-014, ADR-012]
charter_link: charter.md#1-vision--purpose
milestone: unscheduled (future)
---

# PRD-001: Instance Optimization

## Problem
Demo and sub-production instances are often provisioned small and shared. The workbench
already reads each node's memory, CPU and JVM heap at connection (ADR-014) and shows the
worst memory pressure (for example `SUSTAINED_OVER` on a 4-node demo instance), but the
owner cannot act on it: the number is informational only. Slow or memory-starved
instances make live demos and media capture unreliable.

## Users
- Solution Consultants running live demos and captures on instances they do not own.
- Developers using sub-production instances for Fluent SDK work.

## In Scope (must-haves)
- Turn the platform facts we already detect into findings: memory pressure, node status,
  heap use, and demo-hostile system properties.
- Recommend changes that an admin can apply through supported APIs (system properties,
  scheduled jobs, plugin or data clean-up), each with the evidence that triggered it.
- Preview every change as a dry run first, snapshot the prior values, and allow restore,
  reusing the property snapshot mechanism.
- Apply only after explicit user confirmation, one change at a time, with the result
  reported truthfully (a failed apply never reports success).

## Out of Scope (anti-creep fence)
- We will NOT resize hardware, nodes or JVM heap; those belong to the instance owner or
  ServiceNow.
- We will NOT change anything on an instance whose declared purpose is `production`.
- We will NOT run any optimization automatically, on a schedule, or from chat without
  confirmation.
- We will NOT guess: with no detectable cause the feature reports "no actionable finding".
- We will NOT become an instance monitoring or alerting product.

## Acceptance Criteria
- [ ] Each finding cites the detected value that triggered it.
- [ ] Every recommended change has a dry-run preview and a snapshot-backed restore.
- [ ] Applies are refused for `production` instances.
- [ ] A partial or failed apply is reported as failed and leaves a restore handle.
- [ ] Covered by Playwright specs against the real backend using in-memory fakes.

## Success Metrics
- Share of optimization runs that end in a confirmed apply (recommendations are useful).
- Drop in `SUSTAINED_OVER` readings on instances after an apply.
- Zero unconfirmed writes to an instance (audited from operation history).

## Dependencies
- ADR-014 (platform profile detected at connection); ADR-012 (sealed credentials).
- Existing property snapshot and restore engine; operation history.

## Out of Library Scope (always)
Anything that needs ServiceNow-side licensing, hardware or tenant provisioning changes.

## Open Questions
- Which levers can an admin role really change through the Table API or Fluent SDK
  (system properties, scheduled jobs, table cleaner settings), and which need `security_admin`?
- Does the platform expose enough diagnostics (sys_cluster_node_stats history, slow
  transaction logs) to name a cause, or only the current snapshot?
- Is the memory-pressure readout meaningful on shared demo hosts, or noise we should
  down-weight in the UI until this feature exists?
- Needs a roadmap milestone: `.primer/roadmap.md` does not exist yet (`/primer roadmap`).
