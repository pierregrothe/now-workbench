"""Generative UI Tile Catalog schemas and tool-calling models."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TileType = Literal[
    "instance-kpi",
    "instance-card",
    "demo-bundle",
    "security-alert",
    "fluent-schema",
    "rich-text",
    "data-table",
    "media-player",
]

TileLayout = Literal["1-col", "2-col", "3-col", "auto"]


class UITileSpec(BaseModel):
    """Specification for a single Generative UI tile."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(description="Unique identifier for the tile")
    type: TileType = Field(description="Catalog type identifier for the tile")
    title: str = Field(default="", description="Optional human-readable title")
    props: dict[str, Any] = Field(
        default_factory=dict, description="Structured properties passed to the tile component"
    )


class AgentStep(BaseModel):
    """One tool run Otto performed while answering, shown as a step in the conversation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str = Field(description="What the tool reported, in one line")
    ok: bool = Field(default=True, description="False when the tool run failed")


class GenerativeUIResponse(BaseModel):
    """Structured response containing executive summary, multi-tile layout, and tile specs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    summary: str = Field(
        description="Concise 1-sentence executive summary with no excessive markdown"
    )
    layout: TileLayout = Field(
        default="auto", description="Column layout arrangement for multi-tile rendering"
    )
    tiles: list[UITileSpec] = Field(
        default_factory=list, description="List of tiles to display in the session"
    )
    steps: list[AgentStep] = Field(
        default_factory=list, description="Tool runs performed to produce this response"
    )


RENDER_UI_TILES_TOOL = {
    "name": "render_ui_tiles",
    "description": (
        "Render visual ServiceNow Lux interactive tiles in the session instead of markdown text. "
        "Use this tool whenever the user asks for instances, bundles, metrics, schemas, or status."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Concise 1-sentence executive summary with no excessive text.",
            },
            "layout": {
                "type": "string",
                "enum": ["1-col", "2-col", "3-col", "auto"],
                "description": "Grid column layout for the tiles.",
            },
            "tiles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": [
                                "instance-kpi",
                                "instance-card",
                                "demo-bundle",
                                "security-alert",
                                "fluent-schema",
                                "rich-text",
                                "data-table",
                                "media-player",
                            ],
                        },
                        "title": {"type": "string"},
                        "props": {"type": "object"},
                    },
                    "required": ["id", "type", "props"],
                },
            },
        },
        "required": ["summary", "layout", "tiles"],
    },
}


def format_instance_status(status: str | None, fallback: str | None = None) -> str:
    """Format an instance status code into a human-readable real status label."""
    norm = (status or "").strip().lower()
    status_map = {
        "authenticated": "Authenticated (HTTP 200)",
        "unreachable": "Unreachable (Connection Failed)",
        "auth_failed": "Auth Failed (HTTP 401/403)",
        "error": "HTTP Error",
        "unknown": "Unverified (Not Tested)",
    }
    if norm in status_map:
        return status_map[norm]
    if fallback:
        return fallback
    return "Unverified (Not Tested)"


def _summarize_instance_statuses(
    instances: list[dict[str, Any]],
    fallback: str | None = None,
) -> tuple[str, str]:
    """Compute a concise status breakdown string and badge accent color."""
    if not instances:
        return ("No Instances Configured", "amber")
    counts: dict[str, int] = {}
    for inst in instances:
        label = format_instance_status(inst.get("status"), fallback)
        counts[label] = counts.get(label, 0) + 1
    breakdown = ", ".join(f"{cnt} {lbl}" for lbl, cnt in counts.items())
    first_raw = (instances[0].get("status") or "").lower()
    accent = (
        "green"
        if first_raw == "authenticated"
        else "red"
        if first_raw in ("unreachable", "auth_failed", "error")
        else "amber"
    )
    return (breakdown, accent)


def _build_instance_card_tile(
    inst: dict[str, Any],
    idx: int,
    fallback_status: str | None = None,
) -> UITileSpec:
    """Build a single detailed instance-card UITileSpec."""
    inst_id = inst.get("id", f"inst-{idx}")
    raw_status = inst.get("status", "unknown")
    status_label = inst.get("probe_status") or format_instance_status(raw_status, fallback_status)
    actions: list[dict[str, Any]] = [
        {
            "id": "probe",
            "label": "Check Authentication",
            "variant": "primary",
            "instance_id": inst_id,
        },
        {
            "id": "delete_instance",
            "label": "Delete",
            "variant": "secondary",
            "instance_id": inst_id,
        },
        {
            "id": "manage",
            "label": "Edit in Settings",
            "variant": "secondary",
            "instance_id": inst_id,
        },
    ]
    if not inst.get("is_default", False):
        actions.insert(
            1,
            {
                "id": "activate",
                "label": "Set Default",
                "variant": "secondary",
                "instance_id": inst_id,
            },
        )
    return UITileSpec(
        id=f"tile-instance-card-{inst_id}",
        type="instance-card",
        title=inst.get("name", "ServiceNow Instance"),
        props={
            "instance_id": inst_id,
            "name": inst.get("name", "ServiceNow Instance"),
            "url": inst.get("url", ""),
            "release": inst.get("release", "Zurich"),
            "is_default": inst.get("is_default", False),
            "status": raw_status,
            "probe_status": status_label,
            "actions": actions,
        },
    )


def build_instance_response(
    instances: list[dict[str, Any]],
    probe_status: str | None = None,
    detail_level: Literal["summary", "detailed"] = "summary",
) -> GenerativeUIResponse:
    """Build a Generative UI response for instance inquiries (summary first by default)."""
    count = len(instances)
    primary = next(
        (i for i in instances if i.get("is_default")),
        instances[0] if instances else None,
    )
    primary_id = primary.get("id", "default-instance") if primary else ""
    primary_name = primary.get("name", "None") if primary else "None"
    primary_release = primary.get("release", "Zurich") if primary else "Zurich"
    breakdown, accent = _summarize_instance_statuses(instances, probe_status)
    unauth_count = sum(
        1 for i in instances if (i.get("status") or "").strip().lower() not in ("authenticated",)
    )

    kpi_actions: list[dict[str, Any]] = [
        {"id": "show_instances", "label": "Show Instance Details", "variant": "primary"},
        {
            "id": "probe_all",
            "label": "Check Authentication",
            "variant": "secondary",
            "instance_id": primary_id,
        },
        {"id": "manage", "label": "Manage in Settings", "variant": "secondary"},
    ]
    if unauth_count > 0:
        kpi_actions.insert(
            2,
            {
                "id": "delete_unauthenticated",
                "label": f"Delete Unauthenticated ({unauth_count})",
                "variant": "secondary",
            },
        )
    kpi_tile = UITileSpec(
        id="tile-instance-kpi",
        type="instance-kpi",
        title="Instance Summary",
        props={
            "instance_id": primary_id,
            "count": count,
            "label": "Managed Instances" if count != 1 else "Managed Instance",
            "subtitle": f"Primary: {primary_name} ({primary_release}) - {breakdown}",
            "status": breakdown,
            "badge": breakdown if count > 0 else "None",
            "accent": accent,
            "actions": (
                kpi_actions
                if count > 0
                else [{"id": "manage", "label": "Add Instance", "variant": "primary"}]
            ),
        },
    )

    if detail_level == "summary" or count == 0:
        summary_text = (
            f"You manage {count} ServiceNow instance{'s' if count != 1 else ''} ({breakdown}). "
            "Click 'Show Instance Details' or ask for details to inspect each target."
            if count > 0
            else "You have no ServiceNow instances configured yet."
        )
        return GenerativeUIResponse(
            summary=summary_text,
            layout="1-col",
            tiles=[kpi_tile],
        )

    cards = [
        _build_instance_card_tile(inst, idx, probe_status) for idx, inst in enumerate(instances)
    ]
    layout: TileLayout = "3-col" if len(cards) >= 3 else "2-col" if len(cards) == 2 else "1-col"
    suffix = "s" if count != 1 else ""
    return GenerativeUIResponse(
        summary=(
            f"Showing detailed configuration and live status for {count} "
            f"managed ServiceNow instance{suffix}."
        ),
        layout=layout,
        tiles=cards,
    )


_INSTANCE_NOUNS = ("instance", "instande", "instence", "instanse", "target", "targets")
_INSTANCE_VERBS = (
    "how many",
    "count",
    "have",
    "manag",
    "list",
    "show",
    "what",
    "my",
    "active",
    "status",
    "detail",
)
_DETAIL_KEYWORDS = ("detail", "details", "list", "show all", "cards", "expand", "inspect", "which")


def _is_instance_query(lower: str) -> bool:
    """Return True if the normalized query asks about ServiceNow instances."""
    if lower in ("instances", "instandes", "my instances", "targets"):
        return True
    return any(n in lower for n in _INSTANCE_NOUNS) and any(v in lower for v in _INSTANCE_VERBS)


def _wants_detailed_view(lower: str) -> bool:
    """Return True if the user explicitly requested a detailed list or breakdown."""
    return any(kw in lower for kw in _DETAIL_KEYWORDS)


def _build_bundle_response(
    bundle_list: list[dict[str, Any]],
    detailed: bool = True,
) -> GenerativeUIResponse:
    """Build a summary KPI tile or detailed demo-bundle cards."""
    count = len(bundle_list)
    suffix = "s" if count != 1 else ""
    if not detailed:
        total_tables = sum(int(b.get("tables_count", 0)) for b in bundle_list)
        total_records = sum(int(b.get("records_count", 0)) for b in bundle_list)
        kpi = UITileSpec(
            id="tile-bundle-kpi",
            type="instance-kpi",
            title="Demo Recipe Summary",
            props={
                "count": count,
                "label": f"Declarative Demo Recipe{suffix}",
                "subtitle": f"{total_tables} Fluent Tables / {total_records} Seed Records",
                "status": "100% Release Agnostic",
                "badge": "Zero Update Sets",
                "accent": "green",
                "actions": [
                    {"id": "show_bundles", "label": "Show Recipe Details", "variant": "primary"},
                    {"id": "synthesize", "label": "Synthesize New Recipe", "variant": "secondary"},
                    {"id": "inspect", "label": "Open Artifact Library", "variant": "secondary"},
                ],
            },
        )
        return GenerativeUIResponse(
            summary=(
                f"You have {count} declarative demo recipe bundle{suffix} ready. "
                "Click 'Show Recipe Details' to inspect or seed individual bundles."
            ),
            layout="1-col",
            tiles=[kpi],
        )

    tiles: list[UITileSpec] = [
        UITileSpec(
            id=f"tile-bundle-{b.get('id', idx)}",
            type="demo-bundle",
            title=b.get("name", "Demo Bundle"),
            props={
                "bundle_id": b.get("id", ""),
                "name": b.get("name", "Demo Bundle"),
                "industry": b.get("industry", "Cross-Industry"),
                "release": b.get("release", "Zurich"),
                "tables_count": b.get("tables_count", 0),
                "records_count": b.get("records_count", 0),
                "actions": [
                    {
                        "id": "seed",
                        "label": "Seed to Instance",
                        "variant": "primary",
                        "bundle_id": b.get("id", ""),
                    },
                    {
                        "id": "inspect",
                        "label": "Inspect Artifacts",
                        "variant": "secondary",
                        "bundle_id": b.get("id", ""),
                    },
                ],
            },
        )
        for idx, b in enumerate(bundle_list)
    ]
    return GenerativeUIResponse(
        summary=f"You have {count} demo bundle{suffix} ready in the Workbench Artifact Library.",
        layout="2-col" if count >= 2 else "1-col",
        tiles=tiles,
    )


def resolve_query_to_tiles(
    query: str,
    instances: list[dict[str, Any]] | None = None,
    bundles: list[dict[str, Any]] | None = None,
    probe_status: str | None = None,
) -> GenerativeUIResponse:
    """Resolve an incoming natural language inquiry to a structured Generative UI response.

    Summarizes counts first by default unless the user explicitly asks for details or a list.
    """
    lower = query.lower().strip()

    # 1. Instance inquiries (with typo tolerance: instande, instence, instanse, target, manag)
    if _is_instance_query(lower):
        inst_list = (
            instances
            if instances is not None
            else [
                {
                    "id": "inst-primary",
                    "name": "Alec Demo Trial",
                    "url": "https://dev231145.service-now.com",
                    "release": "Zurich",
                    "is_default": True,
                    "status": "unknown",
                }
            ]
        )
        mode: Literal["summary", "detailed"] = (
            "detailed" if _wants_detailed_view(lower) else "summary"
        )
        return build_instance_response(inst_list, probe_status=probe_status, detail_level=mode)

    # 2. Security or risk inquiries (checked before generic 'demo' keyword)
    if any(
        kw in lower
        for kw in (
            "security",
            "risk",
            "risks",
            "alert",
            "alerts",
            "vulnerability",
            "vulnerabilities",
            "remediat",
        )
    ):
        tile = UITileSpec(
            id="tile-security-alert-1",
            type="security-alert",
            title="Ticket Pricing Agent - Access Control Review",
            props={
                "severity": "3 - MEDIUM",
                "agent_name": "Ticket Pricing Agent",
                "issue": "Unrestricted execution path detected for automatic discount approval.",
                "remediation": (
                    "Configure prompt guardrails and require secondary approval in Zurich."
                ),
                "actions": [
                    {
                        "id": "explore_fluent",
                        "label": "Inspect Guardrail Schema",
                        "variant": "primary",
                    },
                    {"id": "manage", "label": "Configure in Settings", "variant": "secondary"},
                ],
            },
        )
        return GenerativeUIResponse(
            summary="1 critical security action item requires AI review.",
            layout="1-col",
            tiles=[tile],
        )

    # 3. Fluent SDK schema inquiries
    if any(kw in lower for kw in ("fluent", "schema", "table", ".now.ts", "typescript")):
        tile_schema = UITileSpec(
            id="tile-fluent-schema-1",
            type="fluent-schema",
            title="Table Definition (Fluent SDK)",
            props={
                "file_path": "src/tables/custom_demo.now.ts",
                "table_name": "x_demo_custom_table",
                "label": "Custom Demo Table",
                "columns_count": 2,
                "code": (
                    "export const my_table = Table({\n"
                    "    name: 'x_demo_custom_table',\n"
                    "    label: 'Custom Demo Table',\n"
                    "    schema: {\n"
                    "        short_desc: Record({ label: 'Short Description', maxLength: 100 }),\n"
                    "        assigned_to: Record({ label: 'Assignee', reference: 'sys_user' }),\n"
                    "    },\n"
                    "})"
                ),
                "actions": [
                    {"id": "explore_fluent", "label": "Open Fluent Explorer", "variant": "primary"},
                ],
            },
        )
        return GenerativeUIResponse(
            summary="ServiceNow Fluent SDK schemas are declared declaratively in *.now.ts files.",
            layout="1-col",
            tiles=[tile_schema],
        )

    # 4. Recipe vs Update Set inquiries
    is_recipe_vs_updateset = any(
        kw in lower for kw in ("update set", "update sets", "sys_update_xml")
    ) or (
        any(kw in lower for kw in ("recipe", "recipes"))
        and not any(kw in lower for kw in ("bundle", "bundles", "package", "packages"))
    )
    if is_recipe_vs_updateset:
        tile_why = UITileSpec(
            id="tile-recipe-why",
            type="rich-text",
            title="Declarative Recipes (No Update Sets)",
            props={
                "body": (
                    "Captured update sets (sys_update_xml) are brittle, contain hardcoded "
                    "sys_ids, and fail on release upgrades. Now Workbench builds demos from "
                    "declarative TypeScript recipes (*.now.ts) + date-aligned seed datasets, "
                    "making them virtually compatible with ANY ServiceNow version "
                    "(Washington, Xanadu, Zurich, Australia)."
                ),
                "actions": [
                    {
                        "id": "explore_fluent",
                        "label": "Explore Fluent Schemas",
                        "variant": "primary",
                    },
                    {"id": "inspect", "label": "View Artifact Library", "variant": "secondary"},
                ],
            },
        )
        tile_compat = UITileSpec(
            id="tile-recipe-compat",
            type="rich-text",
            title="Universal Release Compatibility",
            props={
                "body": (
                    "Demonstration recipes compile into native Table & Metadata API calls during "
                    "transactional seeding. Demos can be re-seeded or torn down cleanly in seconds "
                    "with automated property snapshot restoration."
                ),
                "actions": [
                    {"id": "synthesize", "label": "Synthesize New Recipe", "variant": "secondary"},
                ],
            },
        )
        return GenerativeUIResponse(
            summary=(
                "Now Workbench creates demos based on declarative recipes rather than "
                "captured update sets, ensuring compatibility across any ServiceNow version."
            ),
            layout="2-col",
            tiles=[tile_why, tile_compat],
        )

    # 5. Demo bundle inquiries
    is_bundle_query = any(kw in lower for kw in ("bundle", "bundles", "demo", "demos", "package"))
    if is_bundle_query:
        bundle_list = (
            bundles
            if bundles is not None
            else [
                {
                    "id": "novartis-biohealth-automate-enterpri",
                    "name": "Novartis Clinical Triage Demo",
                    "industry": "Healthcare & Life Sciences",
                    "release": "Zurich",
                    "tables_count": 4,
                    "records_count": 38,
                },
                {
                    "id": "template-customer-service-ai",
                    "name": "Customer Service AI Assistant",
                    "industry": "Customer Service Management",
                    "release": "Xanadu / Zurich",
                    "tables_count": 3,
                    "records_count": 24,
                },
            ]
        )
        is_bundle_count_only = any(
            kw in lower for kw in ("how many", "count")
        ) and not _wants_detailed_view(lower)
        return _build_bundle_response(bundle_list, detailed=not is_bundle_count_only)

    # 6. Default / general inquiry -> clean rich-text card (no markdown wall)
    tile_rich = UITileSpec(
        id="tile-rich-guidance",
        type="rich-text",
        title="Otto Copilot Assistant",
        props={
            "body": (
                f'I received your inquiry: "{query}". '
                "I can summarize your managed instances, showcase demo recipe bundles, "
                "or analyze Fluent SDK schemas in structured cards."
            ),
            "actions": [
                {"id": "show_instances", "label": "Show Managed Instances", "variant": "primary"},
                {"id": "manage", "label": "Workbench Settings", "variant": "secondary"},
                {"id": "explore_fluent", "label": "Explore Fluent SDK", "variant": "secondary"},
            ],
        },
    )
    return GenerativeUIResponse(
        summary="Here is the executive summary for your inquiry.",
        layout="1-col",
        tiles=[tile_rich],
    )
