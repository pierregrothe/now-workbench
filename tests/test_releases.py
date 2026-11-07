"""Tests for ServiceNow platform release hierarchy, compatibility, and workspace resolution."""

from now_workbench.domains.releases.compatibility import (
    compare_releases,
    evaluate_release_prerequisites,
    is_release_compatible,
    normalize_release,
)
from now_workbench.domains.releases.workspaces import resolve_workspace, translate_workspace_url


def test_normalize_release() -> None:
    """Verify release normalization handles various naming conventions."""
    assert normalize_release("rome") == "Rome"
    assert normalize_release("ROME") == "Rome"
    assert normalize_release("san-diego") == "San Diego"
    assert normalize_release("washington dc") == "Washington DC"
    assert normalize_release("washington") == "Washington DC"
    assert normalize_release("wdc") == "Washington DC"
    assert normalize_release("Xanadu") == "Xanadu"
    assert normalize_release("zurich") == "Zurich"


def test_compare_releases_chronology() -> None:
    """Verify releases are compared in strict chronological family order."""
    assert compare_releases("Rome", "San Diego") == -1
    assert compare_releases("San Diego", "Tokyo") == -1
    assert compare_releases("Tokyo", "Utah") == -1
    assert compare_releases("Utah", "Vancouver") == -1
    assert compare_releases("Vancouver", "Washington DC") == -1
    assert compare_releases("Washington DC", "Xanadu") == -1
    assert compare_releases("Xanadu", "Yokohama") == -1
    assert compare_releases("Yokohama", "Zurich") == -1

    assert compare_releases("Xanadu", "Rome") == 1
    assert compare_releases("Zurich", "Washington DC") == 1
    assert compare_releases("Xanadu", "xanadu") == 0


def test_is_release_compatible() -> None:
    """Verify release compatibility checks."""
    assert is_release_compatible("Xanadu", "Rome") is True
    assert is_release_compatible("Zurich", "Xanadu") is True
    assert is_release_compatible("Xanadu", "Xanadu") is True

    # Rome cannot run Xanadu or Washington DC demos
    assert is_release_compatible("Rome", "Xanadu") is False
    assert is_release_compatible("Rome", "Washington DC") is False
    assert is_release_compatible("Utah", "Vancouver") is False


def test_evaluate_release_prerequisites_blocking() -> None:
    """Verify that older releases are rejected when features are unsupported."""
    # Attempting to run AI Agent Studio demo on Rome
    res = evaluate_release_prerequisites(
        instance_release="Rome",
        min_release="Xanadu",
        tags=["AI Agent Studio", "Now Assist GenAI"],
    )
    assert res.is_compatible is False
    assert "below the required minimum release" in res.reason
    assert "AI Agent Studio" in res.unsupported_features

    # Successful evaluation on Zurich instance
    res_ok = evaluate_release_prerequisites(
        instance_release="Zurich",
        min_release="Xanadu",
        tags=["AI Agent Studio"],
    )
    assert res_ok.is_compatible is True
    assert len(res_ok.unsupported_features) == 0


def test_workspace_resolution_evolution() -> None:
    """Verify workspace naming and path resolution adapt across releases."""
    # ITSM: Agent Workspace on Rome vs Service Operations Workspace on San Diego+
    ws_rome = resolve_workspace("itsm", "Rome")
    assert ws_rome.display_name == "Agent Workspace"
    assert ws_rome.path == "/now/workspace/agent/"

    ws_xanadu = resolve_workspace("itsm", "Xanadu")
    assert ws_xanadu.display_name == "Service Operations Workspace"
    assert ws_xanadu.path == "/now/sow/"

    # AI Studio: Not available pre-Xanadu
    ws_ai_rome = resolve_workspace("ai_studio", "Rome")
    assert ws_ai_rome.is_available is False
    assert "Not Available" in ws_ai_rome.display_name

    ws_ai_xanadu = resolve_workspace("ai_studio", "Xanadu")
    assert ws_ai_xanadu.is_available is True
    assert ws_ai_xanadu.display_name == "AI Agent Studio"
    assert ws_ai_xanadu.path == "/now/now-assist-admin/"


def test_translate_workspace_url() -> None:
    """Verify symbolic workspace path translation."""
    assert translate_workspace_url("@workspace/itsm", "Rome") == "/now/workspace/agent"
    assert translate_workspace_url("@workspace/itsm", "Xanadu") == "/now/sow"
    assert translate_workspace_url("@workspace/csm", "Utah") == "/now/csm"
    assert translate_workspace_url("@workspace/ai_studio", "Xanadu") == "/now/now-assist-admin"
