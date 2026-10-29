# now-workbench -- Charter

## 1. Vision
`now-workbench` is an AI-native, containerized developer & demonstration workbench
for the ServiceNow Fluent SDK (`@servicenow/sdk`). It brings together:
1. A portable execution engine for `now-sdk` operations (build, validate, deploy, teardown).
2. A declarative demonstration packaging system (`.sn-demo.zip`) for instant demo staging.
3. An open-standards Web UI built with Lit Web Components faithful to ServiceNow Lux.
4. An embedded **Otto** AI copilot powered by the Anthropic Claude API.
5. A lightweight, powerful CLI for headless automation, CI/CD, and troubleshooting.

## 2. Must-Have Capabilities
- **Docker-First Portability**: Self-contained multi-stage container bundling Python 3.14,
  Node.js LTS, `@servicenow/sdk`, and static Lit web assets.
- **ServiceNow Lux Parity**: Visual design tokens, elevated card surfaces, status pills,
  and responsive navigation mirroring the modern ServiceNow Next Experience / Lux theme.
- **Otto AI Copilot**: Streaming conversational assistant with contextual awareness of
  connected instance, active demo bundle, and `now-sdk` build diagnostics.
- **Demo Bundle Lifecycle**: One-click import, export, inspection, and deployment of
  reproducible bundles containing Fluent `.now.ts` source, Table API seed records,
  system properties, and persona walkthrough guides.
- **Strict Typing & Testability**: 100% type-annotated Python codebase (Pydantic v2,
  strict mypy/pyright) and test suite backed by in-memory fakes (zero brittle mocks).
