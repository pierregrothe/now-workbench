# ADR-002: Otto AI Copilot via Claude API

**Status:** accepted
**Date:** 2026-10-29

## Context
Solution Consultants and Developers need an intelligent conversational assistant to
explain ServiceNow Fluent SDK concepts, diagnose `now-sdk` build errors, and navigate
complex multi-step demonstration scripts.

## Decision
Integrate an embedded **Otto** assistant powered by the Anthropic Claude API (`anthropic` SDK).
The backend maintains an async WebSocket connection streaming Claude completions, with
injected context:
1. Current active demo bundle details.
2. Target ServiceNow instance version, status, and installed plugins.
3. Recent compiler/build error logs.

## Consequences
- Requires `WORKBENCH_ANTHROPIC_API_KEY` for live Claude completions (gracefully degrades
  to helpful simulation mode if unset).
- Otto appears as a first-class drawer in the Lux UI with actionable intent chips.
