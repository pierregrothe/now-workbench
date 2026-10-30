"""Engine that synthesizes Fluent schemas, seed datasets, properties, and SC narratives."""

import json
import re
from pathlib import Path
from typing import Any

from now_workbench.synthesizer.models import (
    SynthesizedDemoResult,
    UseCaseSynthesisRequest,
)


def _slugify(text: str) -> str:
    """Convert arbitrary text into a clean lowercase alphanumeric slug."""
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned[:36] or "custom-demo"


def _table_slug(slug: str, prefix: str = "x_snc") -> str:
    """Convert a bundle slug into a valid ServiceNow scoped table identifier."""
    clean_prefix = re.sub(r"[^a-z0-9_]+", "", prefix.lower()).strip("_") or "x_snc"
    short = re.sub(r"[^a-z0-9]+", "_", slug.lower()).strip("_")[:18]
    return f"{clean_prefix}_{short}_case"


def _build_fluent_source(req: UseCaseSynthesisRequest, table_name: str) -> str:
    """Generate declarative @servicenow/sdk (*.now.ts) table definition."""
    label = f"{req.customer_name} {req.industry} Case"
    return (
        "import { Table, StringColumn, ReferenceColumn, BooleanColumn, IntegerColumn } "
        "from '@servicenow/sdk/core';\n\n"
        f"export const {table_name} = Table({{\n"
        f"  name: '{table_name}',\n"
        f"  label: '{label}',\n"
        "  schema: {\n"
        "    correlation_id: StringColumn({ label: 'Correlation ID', mandatory: true, "
        "maxLength: 40 }),\n"
        "    use_case_summary: StringColumn({ label: 'Use Case Summary', mandatory: true, "
        "maxLength: 255 }),\n"
        "    customer_context: StringColumn({ label: 'Customer Context', mandatory: false, "
        "maxLength: 500 }),\n"
        "    source_incident: ReferenceColumn({ label: 'Source Incident', "
        "referenceTable: 'incident', mandatory: true }),\n"
        "    ai_confidence: IntegerColumn({ label: 'Now Assist Confidence (%)', "
        "mandatory: true }),\n"
        "    automated_remediation: BooleanColumn({ label: 'Automated Remediation', "
        "mandatory: false }),\n"
        "  },\n"
        "});\n"
    )


def _build_seed_records(req: UseCaseSynthesisRequest, table_name: str) -> list[dict[str, Any]]:
    """Synthesize realistic multi-table ServiceNow seed data for the use case."""
    short_uc = req.use_case.strip().rstrip(".")
    return [
        {
            "table": "incident",
            "data": {
                "short_description": f"[{req.customer_name}] {short_uc} - Primary Escalation",
                "description": (
                    f"Customer context ({req.industry}): {req.use_case}. "
                    "Detected anomalous telemetry requiring Now Assist agentic triage."
                ),
                "urgency": "1",
                "impact": "1",
                "category": "inquiry",
            },
        },
        {
            "table": "incident",
            "data": {
                "short_description": (
                    f"[{req.customer_name}] Proactive workflow validation for {req.industry}"
                ),
                "description": (
                    f"Secondary correlated event for {req.customer_name} validating "
                    "automated playbook resolution."
                ),
                "urgency": "2",
                "impact": "2",
                "category": "software",
            },
        },
        {
            "table": table_name,
            "data": {
                "correlation_id": f"AI-{req.customer_name[:4].upper()}-001".strip(),
                "use_case_summary": short_uc[:240],
                "customer_context": f"{req.customer_name} ({req.industry}) - {req.sn_release}",
                "source_incident": "INC0010001",
                "ai_confidence": 96,
                "automated_remediation": True,
            },
        },
    ]


def _extract_persona_parts(persona_str: str, fallback_role: str) -> tuple[str, str]:
    """Split 'Name (Role)' into (name, role)."""
    if "(" in persona_str:
        parts = persona_str.split("(", 1)
        return parts[0].strip(), parts[1].rstrip(")").strip()
    return persona_str.strip(), fallback_role


def _build_narrative_markdown(req: UseCaseSynthesisRequest, title: str, table_name: str) -> str:
    """Create a structured Solution Consultant demonstration narrative and runbook."""
    p1_name, p1_role = _extract_persona_parts(req.persona_primary, "Operations Lead")
    p2_name, p2_role = _extract_persona_parts(req.persona_secondary, "Platform Architect")
    return (
        f"# {title}\n\n"
        f"**Executive Narrative for {req.customer_name} ({req.industry}):** "
        f"{req.use_case} Built on ServiceNow **{req.sn_release}** using the declarative "
        "Fluent SDK and Now Assist.\n\n"
        "## Personas\n\n"
        f"- **{p1_name}** ({p1_role}): Reviews incoming escalations, AI summaries, "
        "and business impact.\n"
        f"- **{p2_name}** ({p2_role}): Oversees the `{table_name}` Fluent data model "
        "and automated playbooks.\n\n"
        "## Walkthrough Stages\n\n"
        "### Step 1: Business Context & Live Intake\n"
        f"**Persona:** {p1_name}\n"
        "**Target Table:** `incident`\n"
        "- Open the Service Operations Workspace and filter by active high-priority incidents "
        f"for {req.customer_name}.\n"
        "- Highlight how fragmented legacy triage slows resolution across teams.\n"
        f"- *Talking Point:* Notice how My ServiceNow brings {req.customer_name}'s critical "
        f"{req.industry} signals into a single conversational workspace.\n\n"
        "### Step 2: Now Assist Agentic Triage & Custom Fluent Model\n"
        f"**Persona:** {p2_name}\n"
        f"**Target Table:** `{table_name}`\n"
        f"- Inspect the synthesized `{table_name}` record correlated with the incident.\n"
        "- Show the 96% Now Assist confidence score and recommended remediation action.\n"
        "- *Talking Point:* Because this table is defined declaratively in Fluent TypeScript "
        "(*.now.ts), your team can version, diff, and deploy customizations in seconds.\n\n"
        "### Step 3: One-Click Resolution & Executive Value Summary\n"
        f"**Persona:** {p1_name}\n"
        "**Target Table:** `incident`\n"
        "- Approve the Now Assist remediation recommendation and verify resolution notes.\n"
        "- Capture an instance screenshot for the customer leave-behind deck.\n"
        f"- *Talking Point:* With ServiceNow {req.sn_release}, {req.customer_name} reduces "
        "mean-time-to-resolution while maintaining full auditability.\n"
    )


class UseCaseSynthesizer:
    """Builds complete .sn-demo bundles from a natural-language use case and context."""

    def __init__(self, bundles_dir: Path) -> None:
        self.bundles_dir = bundles_dir

    def synthesize(
        self,
        req: UseCaseSynthesisRequest,
        author_name: str = "Now Workbench Synthesizer",
        scoped_prefix: str = "x_snc",
    ) -> SynthesizedDemoResult:
        """Generate Fluent code, seed datasets, system properties, and SC narrative."""
        bundle_id = req.bundle_id or _slugify(f"{req.customer_name}-{req.use_case[:28]}")
        bundle_path = self.bundles_dir / bundle_id
        table_name = _table_slug(bundle_id, prefix=scoped_prefix)
        title = f"{req.customer_name}: {req.use_case[:60].strip()}"

        for subdir in ("fluent", "seed", "properties", "walkthrough"):
            (bundle_path / subdir).mkdir(parents=True, exist_ok=True)

        fluent_code = _build_fluent_source(req, table_name)
        seed_records = _build_seed_records(req, table_name)
        sys_props = {
            "glide.ui.polaris.experience": "true",
            "glide.ui.polaris.theme.custom_primary": req.primary_color,
            f"{table_name}.ai_triage.enabled": "true",
            f"{table_name}.customer_org": req.customer_name,
        }
        narrative_md = _build_narrative_markdown(req, title, table_name)

        p1_name, _ = _extract_persona_parts(req.persona_primary, "Operations Lead")
        p2_name, _ = _extract_persona_parts(req.persona_secondary, "Platform Architect")

        manifest_data = {
            "id": bundle_id,
            "name": title,
            "version": "1.0.0",
            "description": f"{req.use_case} (Tailored for {req.customer_name} - {req.industry})",
            "author": author_name,
            "sn_release": req.sn_release,
            "required_plugins": ["com.glide.now.assist", "com.snc.itsm"],
            "tags": [req.industry, req.sn_release, "Synthesized", "GenAI"],
            "personas": [
                {
                    "name": p1_name,
                    "role": req.persona_primary,
                    "email": "presenter@example.com",
                    "notes": f"Primary presenter persona for {req.customer_name}",
                },
                {
                    "name": p2_name,
                    "role": req.persona_secondary,
                    "email": "architect@example.com",
                    "notes": "Technical platform persona",
                },
            ],
        }

        (bundle_path / "manifest.json").write_text(
            json.dumps(manifest_data, indent=2), encoding="utf-8"
        )
        (bundle_path / "fluent" / f"{bundle_id}.now.ts").write_text(fluent_code, encoding="utf-8")
        (bundle_path / "seed" / "01_synthesized_records.json").write_text(
            json.dumps(seed_records, indent=2), encoding="utf-8"
        )
        (bundle_path / "properties" / "sys_properties.json").write_text(
            json.dumps(sys_props, indent=2), encoding="utf-8"
        )
        (bundle_path / "walkthrough" / "guide.md").write_text(narrative_md, encoding="utf-8")

        return SynthesizedDemoResult(
            bundle_id=bundle_id,
            bundle_path=str(bundle_path),
            title=title,
            customer_name=req.customer_name,
            industry=req.industry,
            fluent_table_name=table_name,
            fluent_code=fluent_code,
            seed_records=seed_records,
            sys_properties=sys_props,
            narrative_markdown=narrative_md,
        )
