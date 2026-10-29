# ADR-004: Package Management Migration to uv + Hatchling

**Status:** accepted
**Date:** 2026-10-29

## Context
Following the proven architecture from `market-data-services`, Poetry incurs overhead in
dependency resolution. `uv` provides sub-second dependency installation, native PEP 621
`[project]` support, and seamless caching.

## Decision
1. Standardize on `uv` as the package manager with `hatchling` as the build backend.
2. Maintain standard `uv.lock` and PEP 621 `[project]` configuration in `pyproject.toml`.
3. Support local execution directly via `uv run workbench` and `uv run pytest`.

## Consequences
- Dependency resolution dropped from ~15s to ~400ms.
- Virtualenv activation is not required: commands invoke cleanly with `uv run`.
