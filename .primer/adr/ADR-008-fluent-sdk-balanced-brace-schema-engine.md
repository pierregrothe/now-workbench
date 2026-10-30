# ADR-008: Balanced-Brace Fluent SDK Schema Parser and Diff Engine

**Status:** accepted
**Date:** 2026-10-29

## Context

ServiceNow Fluent SDK applications define platform tables and columns in declarative
TypeScript files (`fluent/*.now.ts`) using nested `Table({ ... })` and `*Column({ ... })`
calls. Solution Consultants and developers need instant schema visualization, column
inspection, and structural diffing between bundles in both the Web UI
(`<now-fluent-explorer>`) and the CLI (`workbench demo fluent inspect/diff`), as well as
contextual schema injection into the Otto AI copilot.

Spawning a Node.js TypeScript compiler subprocess on every schema read or diff request adds
hundreds of milliseconds of latency and requires a full Node toolchain even for read-only
inspection.

## Decision

1. **Zero-Subprocess Balanced-Brace Scanner (`FluentEngine`)**:
   - Implement a deterministic balanced-brace scanner (`_extract_table_blocks`) and column
     extractor in pure Python (`src/now_workbench/fluent/engine.py`) that parses nested
     `Table({ ... })` definitions and column metadata (`StringColumn`, `ReferenceColumn`,
     `BooleanColumn`, `IntegerColumn`, `Record`, etc.).
2. **Structural Schema Diffing (`compute_diff`)**:
   - Compare parsed `FluentTableSchema` lists between any two bundles (`FluentSchemaDiff`)
     to report added tables, removed tables, and per-column modifications.
3. **Interactive Studio Explorer (`<now-fluent-explorer>`)**:
   - Expose `/api/demos/{id}/fluent` and `/api/demos/{id}/fluent/diff` to power the
     ServiceNow Fluent SDK Studio tab in the Web UI.

## Consequences

- Sub-millisecond schema inspection and diffing with zero Node.js subprocess overhead.
- Works identically in offline, containerized, and CI-less local environments.
