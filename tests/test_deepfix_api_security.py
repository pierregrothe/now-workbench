# tests/test_deepfix_api_security.py
# Regression tests for CORS allow-list, WebSocket Origin checks and deploy target resolution.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Deep-fix sec-001, sec-102, sec-103 and the WebSocket Origin part of sec-105."""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from now_workbench.api.app import create_app
from now_workbench.db import InstanceCreate, db_session
from now_workbench.db.repos.instances import InstanceRepository

BUNDLE = "sample-ai-assistant"
GOOD_ORIGIN = "http://localhost:8080"
EVIL_ORIGIN = "https://evil.example.com"


@pytest.fixture
def client() -> TestClient:
    """A test client over the real app (isolated data dir comes from conftest)."""
    return TestClient(create_app())


def test_cors_preflight_foreign_origin_is_not_allowed(client: TestClient) -> None:
    """A foreign origin gets no Access-Control-Allow-Origin header."""
    res = client.options(
        "/api/health",
        headers={"Origin": EVIL_ORIGIN, "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in res.headers


def test_cors_preflight_localhost_origin_is_allowed(client: TestClient) -> None:
    """A localhost origin is echoed back, never the wildcard."""
    res = client.options(
        "/api/health",
        headers={"Origin": GOOD_ORIGIN, "Access-Control-Request-Method": "GET"},
    )
    assert res.headers["access-control-allow-origin"] == GOOD_ORIGIN


@pytest.mark.parametrize("path", ["/ws/logs", "/ws/otto"])
def test_websocket_foreign_origin_is_closed_with_1008(client: TestClient, path: str) -> None:
    """A WebSocket handshake from a foreign Origin is rejected before accept."""
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(path, headers={"Origin": EVIL_ORIGIN}):
            pass
    assert exc.value.code == 1008


def test_websocket_logs_allowed_origin_is_accepted(client: TestClient) -> None:
    """A localhost Origin handshake is accepted."""
    with client.websocket_connect("/ws/logs", headers={"Origin": GOOD_ORIGIN}):
        pass


def test_deploy_unknown_instance_id_returns_404(client: TestClient) -> None:
    """An explicit unresolved instance id never falls back to the default."""
    res = client.post(f"/api/demos/{BUNDLE}/deploy", json={"instance_id": "ghost"})
    assert res.status_code == 404
    assert res.json()["detail"] == "Instance not found"


def test_deploy_without_any_instance_returns_409(client: TestClient) -> None:
    """No instance id and no registered default is a conflict."""
    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        for existing in instance_repo.list_instances():
            instance_repo.delete_instance(existing.id)
    res = client.post(f"/api/demos/{BUNDLE}/deploy", json={})
    assert res.status_code == 409
    assert res.json()["detail"] == "No target instance registered"


def test_deploy_default_instance_reports_target(client: TestClient) -> None:
    """Deploying to the default instance names the target in the response."""
    with db_session() as conn:
        inst = InstanceRepository(conn).add_instance(
            InstanceCreate(name="dev-one", url="https://dev1.service-now.com", is_default=True)
        )
    res = client.post(f"/api/demos/{BUNDLE}/deploy", json={})
    assert res.status_code == 200
    body = res.json()
    assert body["target_instance_id"] == inst.id
    assert body["target_instance_name"] == "dev-one"
