"""Tests for FastAPI endpoints."""

from fastapi.testclient import TestClient
from now_workbench.api.app import create_app


def test_health_check() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["app"] == "now-workbench"


def test_list_demos() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/demos")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(b["manifest"]["id"] == "sample-ai-assistant" for b in data)
