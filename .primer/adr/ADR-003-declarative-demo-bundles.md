# ADR-003: Declarative Demo Bundle Specification (.sn-demo.zip)

**Status:** accepted
**Date:** 2026-10-29

## Context
Demonstration environments suffer from drift, missing mock records, and manual setup
steps across instances.

## Decision
Standardize demonstrations into portable `.sn-demo.zip` archives:
- `manifest.json`: Root metadata (`id`, `name`, `version`, `sn_release`, `personas`, `tags`).
- `fluent/`: ServiceNow Fluent TypeScript source (`*.now.ts`).
- `seed/`: Sequenced JSON files for Table API insertion with tracked `sys_id`s for clean rollback.
- `properties/`: Key-value system property overrides.
- `walkthrough/`: Presenter script (`guide.md`) and persona details.

## Consequences
- Demonstrations become version-controlled, shareable, and fully reproducible with one-click teardown.
