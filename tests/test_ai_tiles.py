"""Tests for Generative UI Tile Catalog schemas and tool-calling models."""

from now_workbench.interfaces.ai.tiles import (
    RENDER_UI_TILES_TOOL,
    GenerativeUIResponse,
    UITileSpec,
    build_instance_response,
    resolve_query_to_tiles,
)


def test_ui_tile_spec_model() -> None:
    """Verify UITileSpec model properties and strict validation."""
    tile = UITileSpec(
        id="tile-1",
        type="instance-kpi",
        title="Instances",
        props={"count": 2, "label": "Instances"},
    )
    assert tile.id == "tile-1"
    assert tile.type == "instance-kpi"
    assert tile.title == "Instances"
    assert tile.props["count"] == 2


def test_generative_ui_response_model() -> None:
    """Verify GenerativeUIResponse serialization and layout validation."""
    tile = UITileSpec(
        id="tile-kpi",
        type="instance-kpi",
        title="KPI",
        props={"count": 1},
    )
    resp = GenerativeUIResponse(
        summary="You have 1 instance.",
        layout="2-col",
        tiles=[tile],
    )
    assert resp.summary == "You have 1 instance."
    assert resp.layout == "2-col"
    assert len(resp.tiles) == 1
    assert RENDER_UI_TILES_TOOL["name"] == "render_ui_tiles"


def test_build_instance_response() -> None:
    """Verify build_instance_response summary-first and detailed layout generation."""
    instances = [
        {
            "id": "inst-1",
            "name": "Alec Demo Trial",
            "url": "https://dev12345.service-now.com",
            "release": "Zurich",
            "is_default": True,
            "status": "authenticated",
        },
        {
            "id": "inst-2",
            "name": "Secondary Sandbox",
            "url": "https://dev99999.service-now.com",
            "release": "Xanadu",
            "is_default": False,
            "status": "unreachable",
        },
    ]
    # Default is summary mode: 1 concise KPI tile with real status breakdown
    summary_resp = build_instance_response(instances)
    assert "2 ServiceNow instances" in summary_resp.summary
    assert "1 Authenticated (HTTP 200)" in summary_resp.summary
    assert "1 Unreachable (Connection Failed)" in summary_resp.summary
    assert summary_resp.layout == "1-col"
    assert len(summary_resp.tiles) == 1
    assert summary_resp.tiles[0].type == "instance-kpi"
    assert len(summary_resp.tiles[0].props["actions"]) == 4
    assert summary_resp.tiles[0].props["actions"][0]["id"] == "show_instances"
    assert summary_resp.tiles[0].props["actions"][1]["id"] == "probe_all"
    assert summary_resp.tiles[0].props["actions"][2]["id"] == "delete_unauthenticated"

    # Detailed mode: individual instance cards with real status and actions
    detail_resp = build_instance_response(instances, detail_level="detailed")
    assert detail_resp.layout == "2-col"
    assert len(detail_resp.tiles) == 2
    assert detail_resp.tiles[0].type == "instance-card"
    assert detail_resp.tiles[0].props["name"] == "Alec Demo Trial"
    assert detail_resp.tiles[0].props["probe_status"] == "Authenticated (HTTP 200)"
    assert detail_resp.tiles[1].props["probe_status"] == "Unreachable (Connection Failed)"

    # Test empty instances
    empty_resp = build_instance_response([])
    assert "no ServiceNow instances" in empty_resp.summary
    assert empty_resp.layout == "1-col"
    assert len(empty_resp.tiles) == 1


def test_resolve_query_to_tiles_typo_handling() -> None:
    """Verify resolve_query_to_tiles summarizes counts first and shows details on request."""
    # User exact prompts with typos -> summary KPI tile only (no unsolicited detail list)
    resp = resolve_query_to_tiles("how many instande I have")
    assert "1 ServiceNow instance" in resp.summary
    assert resp.layout == "1-col"
    assert len(resp.tiles) == 1
    assert resp.tiles[0].type == "instance-kpi"

    resp_manag = resolve_query_to_tiles("how many instance I manag")
    assert "1 ServiceNow instance" in resp_manag.summary
    assert resp_manag.layout == "1-col"
    assert len(resp_manag.tiles) == 1
    assert resp_manag.tiles[0].type == "instance-kpi"

    # Explicit request for details/list -> returns instance-card tiles
    detail_resp = resolve_query_to_tiles("show instance details")
    assert len(detail_resp.tiles) == 1
    assert detail_resp.tiles[0].type == "instance-card"

    # Bundle count vs detailed inquiry
    bundle_count_resp = resolve_query_to_tiles("how many demo bundles do I have")
    assert bundle_count_resp.layout == "1-col"
    assert len(bundle_count_resp.tiles) == 1
    assert bundle_count_resp.tiles[0].type == "instance-kpi"

    bundle_resp = resolve_query_to_tiles("show me demo bundles")
    assert "demo bundle" in bundle_resp.summary
    assert bundle_resp.layout == "2-col"
    assert len(bundle_resp.tiles) == 2
    assert bundle_resp.tiles[0].type == "demo-bundle"

    # Security alert inquiry
    sec_resp = resolve_query_to_tiles("check security risks")
    assert "security" in sec_resp.summary
    assert sec_resp.layout == "1-col"
    assert sec_resp.tiles[0].type == "security-alert"

    # Fluent schema inquiry
    fluent_resp = resolve_query_to_tiles("explain fluent schema")
    assert "Fluent SDK" in fluent_resp.summary
    assert fluent_resp.tiles[0].type == "fluent-schema"

    # General inquiry fallback to rich-text
    gen_resp = resolve_query_to_tiles("hello world")
    assert gen_resp.layout == "1-col"
    assert gen_resp.tiles[0].type == "rich-text"
