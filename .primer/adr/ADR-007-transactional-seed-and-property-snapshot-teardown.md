# ADR-007: Transactional Seed Engine, Snapshot Property Orchestration, and Unified Teardown

**Status:** accepted
**Date:** 2026-10-29

## Context

ServiceNow Solution Consultants frequently run live customer demonstrations on shared or
sub-production instances (`Zurich`, `Xanadu`, `Australia`). Demonstrations mutate two
distinct classes of platform state:
1. **Table API Seed Records** (`seed/*.json`, e.g., sample incidents and AI triage logs).
2. **Instance System Properties** (`properties/sys_properties.json`, e.g., Polaris UI flags
   and confidence thresholds).

Without automated tracking and restoration, repeated demonstrations leave orphaned records
and altered system properties on the target instance.

## Decision

1. **Transactional Seed Tracking (`SeedEngine`)**:
   - Every record inserted via the ServiceNow Table API is recorded in SQLite
     (`seed_operations`) with its target table and `sys_id`.
   - Rollback (`workbench demo rollback <op_id>`) deletes created records in reverse order
     and marks the operation `rolled_back`.
2. **Pre-Apply Property Snapshots (`PropertyEngine`)**:
   - Before applying `properties/sys_properties.json` to a target instance, `PropertyEngine`
     queries the existing values from `/api/now/table/sys_properties` and persists a
     timestamped `PropertySnapshot` JSON artifact on disk.
   - Restoring properties (`workbench demo properties restore`) writes the original snapshot
     values back to the instance.
3. **Unified Demo Reset (`workbench demo reset` / `POST /api/demos/{id}/reset`)**:
   - Combines seed rollback for all active operations on the bundle/instance with system
     property restoration in a single idempotent teardown operation.

## Consequences

- Demonstrations can be staged and torn down repeatedly without polluting shared instances.
- Full simulation support (`fake_mode=True`) allows testing seed and property lifecycles
  offline with zero network calls.
