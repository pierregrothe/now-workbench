# now-workbench -- Product Vision

## Target Personas

1. **ServiceNow Solution Consultants (SCs) & Technical Architects**:
   - Need to rapidly stand up, customize, reset, and tear down customer-tailored
     demonstrations without polluting shared sub-prod or developer instances.
   - Require 1-click import/export of demo packages to share with team members.
2. **Now Platform Developers**:
   - Building scoped applications with the modern ServiceNow Fluent SDK (`*.now.ts`).
   - Need rapid build verification, schema diffing, and live diagnostic feedback.
3. **Coding Agents (Argon / Opus)**:
   - Pair-program with SCs and developers to generate Fluent schemas, synthesize mock
     data, troubleshoot build errors, and maintain project code.

## Key Product Surfaces

### 1. Web Dashboard (ServiceNow Lux Experience)
- **Top Shell**: Instance connection indicator (`dev12345.service-now.com [Xanadu] ●`),
  workspace selector, global `Cmd+K` command palette.
- **Nav Rail**: Vertical icon navigation (Demos, Studio, Seed Data, Diagnostics, Settings).
- **Demo Catalog**: Visual grid of installed & available demo bundles with release tags,
  active status, and actions: `Deploy to Instance`, `Export Bundle`, `Reset Seed Data`.
- **Live Terminal / Console**: Real-time streaming output of `now-sdk build` and
  deployment steps with ANSI colorization.

### 2. Otto AI Copilot
- Slide-in side drawer featuring ServiceNow's Otto visual persona.
- Real-time streaming conversational interface via Anthropic Claude API.
- Deep workspace context injection: active demo bundle, target instance version,
  compiler output.
- Interactive action pills: "Diagnose build failure", "Generate seed data", "Export bundle".

### 3. Headless CLI (`workbench`)
- `workbench doctor`: Checks Node.js, `now-sdk`, Python, and instance connectivity.
- `workbench demo list`: Displays local demo packages.
- `workbench demo build <bundle>`: Compiles Fluent TypeScript in a clean workspace.
- `workbench demo deploy <bundle> [--instance <profile>]`: Full build & push to instance.
- `workbench demo export <bundle> -o <file.zip>`: Exports self-contained bundle.
- `workbench serve [--port 8080]`: Starts the FastAPI server and serves the Lux web UI.
