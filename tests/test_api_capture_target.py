# tests/test_api_capture_target.py
# Capture never falls back to a hardcoded instance (deep-review err-109).
# Author: Pierre Grothe
# Date: 2026-11-06
"""The capture route resolves a real target instance or fails loudly."""

import pytest
from fastapi.testclient import TestClient

from now_workbench.domains.instances.repository import InstanceRepository
from now_workbench.interfaces.api.app import create_app
from now_workbench.platform.db.session import db_session

_BODY = {
    "bundle_id": "sample-ai-assistant",
    "target_path": "/now/nav/ui/classic",
    "media_type": "screenshot",
    "fake_mode": True,
}


@pytest.fixture
def client() -> TestClient:
    """A test client over the real app (isolated data dir comes from conftest)."""
    return TestClient(create_app())


def test_create_capture_unknown_instance_id_returns_not_found(client: TestClient) -> None:
    """An explicit instance id that does not resolve is a 404, never a hardcoded fallback."""
    res = client.post(
        "/api/demos/sample-ai-assistant/captures", json={**_BODY, "instance_id": "ghost"}
    )
    assert res.status_code == 404
    assert "Instance not found" in res.json()["detail"]


def test_create_capture_without_any_instance_returns_conflict(client: TestClient) -> None:
    """With no instance id and nothing registered there is no target, so the route says so."""
    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        for inst in instance_repo.list_instances():
            instance_repo.delete_instance(inst.id)
    res = client.post("/api/demos/sample-ai-assistant/captures", json=_BODY)
    assert res.status_code == 409
    assert "No target instance registered" in res.json()["detail"]
