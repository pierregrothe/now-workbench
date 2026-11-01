# Acme Corp: Automated HR Onboarding and Equipment Provisioning with Empl

**Executive Narrative for Acme Corp (Human Resources):** Automated HR Onboarding and Equipment Provisioning with Employee Center Built on ServiceNow **Utah** using the declarative Fluent SDK and Now Assist.

## Personas

- **Sarah Jenkins** (Service Desk Lead): Reviews incoming escalations, AI summaries, and business impact.
- **Marcus Vance** (Platform Architect): Oversees the `x_snc_hr_onboarding_ai_case` Fluent data model and automated playbooks.

## Walkthrough Stages

### Step 1: Business Context & Live Intake
**Persona:** Sarah Jenkins
**Target Table:** `incident`
- Open the Service Operations Workspace and filter by active high-priority incidents for Acme Corp.
- Highlight how fragmented legacy triage slows resolution across teams.
- *Talking Point:* Notice how My ServiceNow brings Acme Corp's critical Human Resources signals into a single conversational workspace.

### Step 2: Now Assist Agentic Triage & Custom Fluent Model
**Persona:** Marcus Vance
**Target Table:** `x_snc_hr_onboarding_ai_case`
- Inspect the synthesized `x_snc_hr_onboarding_ai_case` record correlated with the incident.
- Show the 96% Now Assist confidence score and recommended remediation action.
- *Talking Point:* Because this table is defined declaratively in Fluent TypeScript (*.now.ts), your team can version, diff, and deploy customizations in seconds.

### Step 3: One-Click Resolution & Executive Value Summary
**Persona:** Sarah Jenkins
**Target Table:** `incident`
- Approve the Now Assist remediation recommendation and verify resolution notes.
- Capture an instance screenshot for the customer leave-behind deck.
- *Talking Point:* With ServiceNow Utah, Acme Corp reduces mean-time-to-resolution while maintaining full auditability.
