# now-workbench -- Product Vision & Capabilities

## Target Personas

1. **ServiceNow Solution Consultants (Advisory & Field SCs)**:
   - Need to rapidly discover, clone, tailor, deliver, and tear down customer-specific demos.
   - Deliver high-impact customer meetings with guided persona journeys, stage verification,
     and backup media recordings.
2. **Now Platform Developers & Architects**:
   - Building scoped applications with the modern ServiceNow Fluent SDK (`*.now.ts`).
   - Requiring schema diffing, build verification, and clean instance deployment.
3. **Otto AI Copilot (Claude API)**:
   - Autonomous use-case synthesizer that generates customer datasets, Fluent tables,
     and SC narratives on demand.

## Core Workspaces & Surfaces

### 1. Home & AI Intent Hub
- Conversational-first entrance with top chat input.
- Real-time intent classification that automatically transitions to the relevant workspace
  and docks the chat dock at the bottom of the page.

### 2. Solution Consultant Studio (Use-Case Synthesizer)
- Natural-language use-case synthesis generating multi-table seed data, Fluent `.now.ts` code,
  and structured Solution Consultant walkthrough playbooks.

### 3. Artifact Library & Demo Lifecycle (DemoHub Catalog Replacement)
- Searchable catalog of packaged `.sn-demo` bundles with release tags and persona profiles.
- 1-click "Clone & Customize for Customer" (duplicate baseline before editing).
- Transactional seed engine with dynamic Date Wizard and 1-click teardown/rollback.

### 4. Presenter HUD & Execution Console
- Presenter HUD with persona switching, stage-by-stage talking points, and live instance verification.
- Integrated Safe Harbor disclaimer banner for store deltas and preview features.

### 5. Media Capture Studio
- High-resolution screenshot and video capture directly from the workspace.

### 6. Workbench Settings & Security Vault
- Strict API key lifecycle: requires explicit key deletion before entering a new key.
- Live API key validation against the Claude API prior to acceptance.
- Authenticated encryption at rest in local vault with masked key preview.
