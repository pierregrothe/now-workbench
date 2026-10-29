# ADR-001: Hybrid Runtime with Python Core & Lit Web Components

**Status:** accepted
**Date:** 2026-10-29

## Context
The ServiceNow SDK (`@servicenow/sdk`) runs on Node.js and uses TypeScript. However, for
rapid backend orchestration, data validation, and coding agent velocity (Gemini Argon,
Claude Opus), Python 3.14 with Pydantic v2 offers higher safety and ergonomics.
Furthermore, the user interface must faithfully replicate the modern ServiceNow Lux
design language.

## Decision
1. Core backend, CLI, and REST/WebSocket API implemented in **Python 3.14** (FastAPI + Typer).
2. Frontend implemented in **Lit Web Components** (TypeScript + Vite) mimicking ServiceNow's
   native Next Experience component architecture (`now-*`) and Lux tokens.
3. Unified packaging in a multi-stage Docker container.

## Consequences
- The container bundles both Node.js (for `@servicenow/sdk`) and Python 3.14.
- Clean separation between frontend components and backend orchestration.
