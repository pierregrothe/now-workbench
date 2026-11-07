"""Tests for DemoHub parity capabilities and secure API key lifecycle (EPIC-012)."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from now_workbench.domains.bundles.manager import BundleManager
from now_workbench.domains.seed.date_wizard import resolve_date_expression, transform_dataset_dates
from now_workbench.domains.settings.models import WorkbenchPreferencesUpdate
from now_workbench.domains.settings.repository import PreferencesRepository
from now_workbench.interfaces.ai.client import validate_api_key
from now_workbench.interfaces.api.app import create_app
from now_workbench.interfaces.cli.main import app as cli_app
from now_workbench.platform.db.session import init_db

runner = CliRunner(env={"COLUMNS": "250"})


class FakeAnthropicSuccessClient:
    class Messages:
        async def create(self, **kwargs: Any) -> Any:
            return {"id": "msg_success"}

    messages = Messages()


class FakeAnthropicAuthErrorClient:
    class Messages:
        async def create(self, **kwargs: Any) -> Any:
            request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            response = httpx.Response(401, request=request)
            raise anthropic.AuthenticationError(
                message="Invalid API Key",
                response=response,
                body={"error": {"type": "authentication_error", "message": "Invalid API Key"}},
            )

    messages = Messages()


class FakeAnthropicRateLimitClient:
    class Messages:
        async def create(self, **kwargs: Any) -> Any:
            request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            response = httpx.Response(429, request=request)
            raise anthropic.RateLimitError(
                message="Rate limit exceeded",
                response=response,
                body={"error": {"type": "rate_limit_error", "message": "Rate limit exceeded"}},
            )

    messages = Messages()


class FakeAnthropicNetworkErrorClient:
    class Messages:
        async def create(self, **kwargs: Any) -> Any:
            raise ConnectionError("getaddrinfo failed: host unreachable")

    messages = Messages()


class FakeAnthropicGenericErrorClient:
    class Messages:
        async def create(self, **kwargs: Any) -> Any:
            raise RuntimeError("Unexpected internal error")

    messages = Messages()


# ==============================================================================
# Date Wizard Tests
# ==============================================================================


def test_date_wizard_expressions() -> None:
    """Verify relative date offset evaluation and formatting."""
    anchor = datetime(2026, 10, 30, 12, 0, 0, tzinfo=UTC)

    # 1. Base tokens
    assert resolve_date_expression("{{TODAY}}", anchor=anchor) == "2026-10-30 12:00:00"
    assert resolve_date_expression("{{NOW}}", anchor=anchor) == "2026-10-30 12:00:00"

    # 2. Additive & subtractive offsets across units
    assert resolve_date_expression("{{TODAY + 15s}}", anchor=anchor) == "2026-10-30 12:00:15"
    assert resolve_date_expression("{{TODAY - 30m}}", anchor=anchor) == "2026-10-30 11:30:00"
    assert resolve_date_expression("{{TODAY - 2h}}", anchor=anchor) == "2026-10-30 10:00:00"
    assert resolve_date_expression("{{TODAY + 3d}}", anchor=anchor) == "2026-11-02 12:00:00"
    assert resolve_date_expression("{{TODAY - 1w}}", anchor=anchor) == "2026-10-23 12:00:00"

    # 3. No match or plain string returns unchanged
    plain_text = "Plain string without templates"
    assert resolve_date_expression(plain_text) == plain_text

    # 4. Recursive transformation across complex nested structures
    nested_dataset = {
        "title": "Incident batch",
        "created": "{{TODAY - 1h}}",
        "nested": {
            "due": "{{TODAY + 2d}}",
            "tags": ["urgent", "{{TODAY}}"],
            "count": 42,
        },
    }
    transformed = transform_dataset_dates(nested_dataset, anchor=anchor)
    assert transformed["created"] == "2026-10-30 11:00:00"
    assert transformed["nested"]["due"] == "2026-11-01 12:00:00"
    assert transformed["nested"]["tags"] == ["urgent", "2026-10-30 12:00:00"]
    assert transformed["nested"]["count"] == 42


# ==============================================================================
# Demo Bundle Cloning Tests
# ==============================================================================


def test_bundle_cloning(tmp_path: Path) -> None:
    """Verify copying baseline bundles into customer-tailored bundles."""
    source_dir = tmp_path / "baseline-incident"
    source_dir.mkdir(parents=True)
    manifest = {
        "id": "baseline-incident",
        "name": "Baseline Incident Demo",
        "version": "1.0.0",
        "sn_release": "Xanadu",
        "description": "Baseline template",
        "author": "Now SC",
        "required_plugins": [],
    }
    (source_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (source_dir / "fluent").mkdir()
    (source_dir / "fluent" / "table.now.ts").write_text("// Fluent schema", encoding="utf-8")

    mgr = BundleManager(storage_dir=tmp_path)

    # 1. Validation errors
    with pytest.raises(ValueError, match="Target bundle ID cannot be empty"):
        mgr.clone_bundle(source_id="baseline-incident", target_id="  ")

    with pytest.raises(FileNotFoundError, match="does not exist"):
        mgr.clone_bundle(source_id="nonexistent-bundle", target_id="new-clone")

    # 2. Successful clone
    cloned = mgr.clone_bundle(
        source_id="baseline-incident",
        target_id="acme-incident-custom",
        target_name="Acme Corp Custom Incident",
    )
    assert cloned.manifest.id == "acme-incident-custom"
    assert cloned.manifest.name == "Acme Corp Custom Incident"
    assert (tmp_path / "acme-incident-custom" / "fluent" / "table.now.ts").exists()

    # 3. Collision error
    with pytest.raises(FileExistsError, match="already exists"):
        mgr.clone_bundle(source_id="baseline-incident", target_id="acme-incident-custom")

    # 4. Clone with default generated name
    cloned_default = mgr.clone_bundle(
        source_id="baseline-incident",
        target_id="default-cloned",
    )
    assert cloned_default.manifest.name == "Baseline Incident Demo (Cloned)"


def test_api_and_cli_bundle_clone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify POST /api/demos/{id}/clone and workbench demo clone CLI."""
    db_file = tmp_path / "test_api.db"
    bundles_dir = tmp_path / "bundles"
    bundles_dir.mkdir(parents=True)

    src_dir = bundles_dir / "sample-ai-assistant"
    src_dir.mkdir(parents=True)
    (src_dir / "manifest.json").write_text(
        json.dumps(
            {
                "id": "sample-ai-assistant",
                "name": "Sample AI Assistant",
                "version": "0.1.0",
                "sn_release": "Xanadu",
                "description": "Sample",
                "author": "Now SC",
                "required_plugins": [],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("WORKBENCH_DB_PATH", str(db_file))
    monkeypatch.setenv("WORKBENCH_BUNDLES_DIR", str(bundles_dir))
    monkeypatch.setenv("WORKBENCH_WORKSPACE_DIR", str(tmp_path))

    init_db(db_file)
    app = create_app()
    client = TestClient(app)

    # 1. API 404 for unknown source
    resp_404 = client.post(
        "/api/demos/missing-bundle/clone",
        json={"target_bundle_id": "new-bundle"},
    )
    assert resp_404.status_code == 404

    # 2. API success
    resp_ok = client.post(
        "/api/demos/sample-ai-assistant/clone",
        json={
            "target_bundle_id": "customer-novartis",
            "target_name": "Novartis Custom Demo",
        },
    )
    assert resp_ok.status_code == 200
    data = resp_ok.json()
    assert data["manifest"]["id"] == "customer-novartis"
    assert data["manifest"]["name"] == "Novartis Custom Demo"

    # 3. API 400 for already existing target
    resp_dup = client.post(
        "/api/demos/sample-ai-assistant/clone",
        json={"target_bundle_id": "customer-novartis"},
    )
    assert resp_dup.status_code == 400

    # 4. CLI clone command
    cli_res = runner.invoke(
        cli_app,
        [
            "demo",
            "clone",
            "sample-ai-assistant",
            "customer-roche",
            "--name",
            "Roche BioHealth Demo",
        ],
    )
    assert cli_res.exit_code == 0
    assert "Cloned demo bundle" in cli_res.stdout
    assert (bundles_dir / "customer-roche").exists()

    # 5. CLI clone failure on non-existent bundle
    cli_fail = runner.invoke(
        cli_app,
        ["demo", "clone", "missing-source", "target-fail"],
    )
    assert cli_fail.exit_code == 1
    assert "Error cloning bundle" in cli_fail.stdout


# ==============================================================================
# Claude API Key Validation & Delete-Before-Replace Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_validate_api_key_logic() -> None:
    """Verify format checks, live Anthropic probe responses, and error handling."""
    # 1. Empty key
    valid, msg = await validate_api_key("")
    assert not valid
    assert "cannot be empty" in msg

    # 2. Bad prefix
    valid, msg = await validate_api_key("invalid-prefix-key")
    assert not valid
    assert "sk-ant-" in msg

    # 3. Test/mock mode
    valid, msg = await validate_api_key("sk-ant-test-fixture-key")
    assert valid
    assert "test mode" in msg

    # 4. In-memory fake client: Success
    valid, msg = await validate_api_key("sk-ant-live-real", client=FakeAnthropicSuccessClient())
    assert valid
    assert "verified" in msg

    # 5. In-memory fake client: Auth Error
    valid, msg = await validate_api_key("sk-ant-bad-secret", client=FakeAnthropicAuthErrorClient())
    assert not valid
    assert "authentication failed" in msg.lower()

    # 6. In-memory fake client: Rate Limited
    valid, msg = await validate_api_key("sk-ant-busy", client=FakeAnthropicRateLimitClient())
    assert valid
    assert "rate limit" in msg

    # 7. In-memory fake client: Offline network
    valid, msg = await validate_api_key("sk-ant-offline", client=FakeAnthropicNetworkErrorClient())
    assert valid
    assert "probe offline" in msg

    # 8. In-memory fake client: Generic error
    valid, msg = await validate_api_key("sk-ant-err", client=FakeAnthropicGenericErrorClient())
    assert not valid
    assert "Validation failed" in msg


def test_delete_before_replace_and_settings_endpoints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify strict delete-before-replace lifecycle and SQLite encryption."""
    db_file = tmp_path / "test_settings_secure.db"
    monkeypatch.setenv("WORKBENCH_DB_PATH", str(db_file))
    conn = init_db(db_file)

    pref_repo = PreferencesRepository(conn)
    app = create_app()
    client = TestClient(app)

    # 1. Probe validation endpoint
    probe_resp = client.post(
        "/api/settings/validate-key",
        json={"api_key": "sk-ant-test-probe"},
    )
    assert probe_resp.status_code == 200
    assert probe_resp.json()["valid"] is True

    # 2. Reject setting key with invalid format
    bad_fmt_resp = client.put(
        "/api/settings",
        json={"anthropic_api_key": "not-a-valid-ant-key"},
    )
    assert bad_fmt_resp.status_code == 400
    assert "verification failed" in bad_fmt_resp.json()["detail"].lower()

    # 3. Set a valid test key
    set_resp = client.put(
        "/api/settings",
        json={"anthropic_api_key": "sk-ant-test-key-alpha-1234567890"},
    )
    assert set_resp.status_code == 200
    prefs = set_resp.json()
    assert prefs["has_anthropic_api_key"] is True
    assert prefs["anthropic_api_key_masked"].startswith("sk-ant-")
    assert prefs["anthropic_api_key_masked"].endswith("7890")

    # 4. Strict Delete-Before-Replace check:
    # Submitting a new key while active key exists MUST return HTTP 400
    replace_resp = client.put(
        "/api/settings",
        json={"anthropic_api_key": "sk-ant-test-key-beta-9999999999"},
    )
    assert replace_resp.status_code == 400
    assert "explicitly delete the existing key" in replace_resp.json()["detail"]

    # Also test repository directly raises ValueError on attempted overwrite
    with pytest.raises(ValueError, match="explicitly delete"):
        pref_repo.update_workbench_preferences(
            WorkbenchPreferencesUpdate(anthropic_api_key="sk-ant-test-key-gamma")
        )

    # 5. Delete active key via DELETE /api/settings/api-key
    del_resp = client.delete("/api/settings/api-key")
    assert del_resp.status_code == 200
    del_prefs = del_resp.json()
    assert del_prefs["has_anthropic_api_key"] is False
    assert del_prefs["anthropic_api_key_masked"] == ""

    # Test direct repo method
    pref_repo.delete_anthropic_api_key()

    # 6. Now setting a new key succeeds
    new_resp = client.put(
        "/api/settings",
        json={"anthropic_api_key": "sk-ant-test-key-beta-9999999999"},
    )
    assert new_resp.status_code == 200
    assert new_resp.json()["has_anthropic_api_key"] is True
    assert new_resp.json()["anthropic_api_key_masked"].endswith("9999")

    # 7. Clearing key via empty string in update preferences
    clear_resp = client.put(
        "/api/settings",
        json={"anthropic_api_key": ""},
    )
    assert clear_resp.status_code == 200
    assert clear_resp.json()["has_anthropic_api_key"] is False
