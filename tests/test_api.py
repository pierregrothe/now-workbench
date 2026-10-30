"""Tests for FastAPI endpoints."""

import pytest
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


def test_seed_and_rollback_api_endpoints() -> None:
    """Verify demo seed and rollback API routes in fake mode."""
    app = create_app()
    client = TestClient(app)

    # 1. Seed records in fake mode
    seed_resp = client.post(
        "/api/demos/sample-ai-assistant/seed",
        json={"fake_mode": True},
    )
    assert seed_resp.status_code == 200
    seed_data = seed_resp.json()
    op_id = seed_data["id"]
    assert seed_data["bundle_id"] == "sample-ai-assistant"
    assert seed_data["status"] == "completed"
    assert len(seed_data["created_records"]) == 2

    # 2. Check operations history
    ops_resp = client.get("/api/demos/seed/operations")
    assert ops_resp.status_code == 200
    ops = ops_resp.json()
    assert any(o["id"] == op_id for o in ops)

    # 3. Rollback operation
    rb_resp = client.post(
        f"/api/demos/seed/{op_id}/rollback?fake_mode=true",
    )
    assert rb_resp.status_code == 200
    rb_data = rb_resp.json()
    assert rb_data["success"] is True
    assert rb_data["deleted_count"] == 2


def test_teardown_demo_endpoint_with_active_seed_operations() -> None:
    """Verify demo teardown rolls back active seed operations and restores properties."""
    app = create_app()
    client = TestClient(app)

    # 1. Seed records in fake mode to establish an active completed operation
    seed_resp = client.post(
        "/api/demos/sample-ai-assistant/seed",
        json={"fake_mode": True},
    )
    assert seed_resp.status_code == 200

    # 2. Reset / Teardown demo
    td_resp = client.post(
        "/api/demos/sample-ai-assistant/reset",
        json={"fake_mode": True},
    )
    assert td_resp.status_code == 200
    td_data = td_resp.json()
    assert td_data["bundle_id"] == "sample-ai-assistant"
    assert td_data["seed_records_rolled_back"] >= 2


def test_ws_logs_endpoint() -> None:
    """Verify live WebSocket logs streaming endpoint connects and accepts messages."""
    app = create_app()
    client = TestClient(app)
    with client.websocket_connect("/ws/logs") as websocket:
        websocket.send_text("client_ping")


@pytest.mark.asyncio
async def test_log_broadcaster_disconnect() -> None:
    """Verify LogBroadcaster handles connection failures gracefully."""
    from typing import Any

    from now_workbench.api.app import LogBroadcaster

    broadcaster = LogBroadcaster()
    # Broadcast to empty connections
    await broadcaster.broadcast("test message")
    assert broadcaster.active_connections == []

    # Broadcast with failing websocket
    class BrokenWebSocket:
        async def send_json(self, data: Any) -> None:
            raise ConnectionResetError("Connection lost")

    broken_ws = BrokenWebSocket()
    broadcaster.active_connections.append(broken_ws)  # type: ignore[arg-type]
    await broadcaster.broadcast("broken test")
    assert broadcaster.active_connections == []


def test_seed_database_populated_and_empty() -> None:
    """Verify seed_database handles populated vs empty repository."""
    from now_workbench.api.app import seed_database
    from now_workbench.config.settings import settings
    from now_workbench.db import DatabaseRepository, InstanceCreate, init_db

    conn = init_db(":memory:")
    repo = DatabaseRepository(conn)
    repo.add_instance(
        InstanceCreate(id="existing", name="Existing", url="https://e.sn.com", is_default=True)
    )
    seed_database(repo)
    instances = repo.list_instances()
    assert len(instances) == 1
    assert instances[0].id == "existing"
    conn.close()

    old_url = settings.sn_instance_url
    try:
        settings.sn_instance_url = "https://seed-test.service-now.com"
        empty_conn = init_db(":memory:")
        empty_repo = DatabaseRepository(empty_conn)
        seed_database(empty_repo)
        assert len(empty_repo.list_instances()) == 1
        assert empty_repo.list_instances()[0].id == "default-instance"
        empty_conn.close()
    finally:
        settings.sn_instance_url = old_url


def test_generative_ui_tiles_api() -> None:
    """Verify POST /api/ai/tiles returns structured multi-tile response without markdown slop."""
    app = create_app()
    client = TestClient(app)

    # 1. Test instance count inquiry -> summary KPI tile first
    resp = client.post("/api/ai/tiles", json={"query": "how many instande I have"})
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "layout" in data
    assert "tiles" in data
    assert data["layout"] == "1-col"
    assert len(data["tiles"]) == 1
    assert data["tiles"][0]["type"] == "instance-kpi"

    # 1b. Test detailed instance inquiry -> individual instance-card tiles
    detail_resp = client.post("/api/ai/tiles", json={"query": "show instance details"})
    assert detail_resp.status_code == 200
    d_data = detail_resp.json()
    assert len(d_data["tiles"]) >= 1
    assert d_data["tiles"][0]["type"] == "instance-card"

    # 2. Test bundle inquiry
    bundle_resp = client.post("/api/ai/tiles", json={"query": "what bundles do I have"})
    assert bundle_resp.status_code == 200
    b_data = bundle_resp.json()
    assert b_data["layout"] == "2-col"
    assert b_data["tiles"][0]["type"] == "demo-bundle"


def test_delete_demo_bundle_api() -> None:
    """Verify DELETE /api/demos/{bundle_id} clones a temp bundle, deletes it, and checks 404."""
    app = create_app()
    client = TestClient(app)

    # 1. Clone sample bundle to a temporary test artifact
    clone_resp = client.post(
        "/api/demos/sample-ai-assistant/clone",
        json={"target_bundle_id": "test-to-delete-artifact", "target_name": "Temporary Demo"},
    )
    assert clone_resp.status_code == 200

    # 2. Delete the cloned artifact
    del_resp = client.delete("/api/demos/test-to-delete-artifact")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # 3. Trying to delete again returns 404
    del_404 = client.delete("/api/demos/test-to-delete-artifact")
    assert del_404.status_code == 404


def test_delete_demo_capture_api() -> None:
    """Verify creating and deleting a media capture artifact via API."""
    app = create_app()
    client = TestClient(app)

    # 1. Clone sample bundle to an isolated test artifact
    clone_resp = client.post(
        "/api/demos/sample-ai-assistant/clone",
        json={"target_bundle_id": "test-capture-bundle", "target_name": "Test Capture Demo"},
    )
    assert clone_resp.status_code == 200

    try:
        # 2. Create a simulated screenshot capture on test-capture-bundle
        cap_resp = client.post(
            "/api/demos/test-capture-bundle/captures",
            json={
                "bundle_id": "test-capture-bundle",
                "target_path": "/incident_list.do",
                "media_type": "screenshot",
                "label": "Test Capture To Delete",
                "fake_mode": True,
            },
        )
        assert cap_resp.status_code == 200
        filename = cap_resp.json()["filename"]

        # 3. Delete the capture
        del_resp = client.delete(f"/api/demos/test-capture-bundle/captures/{filename}")
        assert del_resp.status_code == 200
        assert del_resp.json()["success"] is True

        # 4. Deleting again returns 404
        del_404 = client.delete(f"/api/demos/test-capture-bundle/captures/{filename}")
        assert del_404.status_code == 404
    finally:
        client.delete("/api/demos/test-capture-bundle")
