# now-workbench -- Project Brief

## What it is

`now-workbench` is a containerized, AI-native developer and demonstration workbench
for the ServiceNow Fluent SDK (`@servicenow/sdk`). It unifies:
1. An async execution engine for the Fluent SDK toolchain (`build`, `deploy`, `validate`).
2. A declarative demonstration packaging system (`.sn-demo.zip`) for repeatable demo staging and teardown.
3. An open-standard Web UI built with Lit Web Components faithful to the ServiceNow Lux design system.
4. An embedded **Otto** AI assistant powered by the Anthropic Claude API for guided demo navigation and troubleshooting.
5. A lightweight Typer CLI for headless automation and diagnostics.

## Origin & Purpose

Created by Pierre Grothe (pierre@grothe.ca) in October 2026 to solve key bottlenecks
faced by ServiceNow Solution Consultants and Platform Developers:
- Demonstrations frequently drift, corrupt shared sub-prods, or require cumbersome manual setup.
- Scoped apps built via `@servicenow/sdk` lack a dedicated lightweight playground with mock data generation.
- SCs need an intuitive interface that replicates ServiceNow's modern Lux aesthetic while keeping build and deploy workflows containerized and portable.

## Core Architecture

- **Backend**: Python 3.14.10, FastAPI, Typer, Pydantic v2, uv package management.
- **Frontend**: Lit 3.x (Web Components), TypeScript, Vite, ServiceNow Lux design tokens.
- **Copilot**: Otto side-drawer streaming Claude completions with injected workspace context.
- **Portability**: Multi-stage Docker container bundling Python 3.14 + Node.js LTS + `@servicenow/sdk`.
