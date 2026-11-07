# src/now_workbench/interfaces/ai/tile_builders.py
# Builds instance and bundle tiles, and routes a keyless query to the right tiles.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tile builders: instance cards and KPIs, bundle lists, keyless query routing."""

from typing import Any, Literal

from now_workbench.interfaces.ai.tiles import GenerativeUIResponse, TileLayout, UITileSpec

__all__ = ["build_instance_response", "format_instance_status"]


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
