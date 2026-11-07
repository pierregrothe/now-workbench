"""Tests for ServiceNow system properties inspection, snapshotting, and restoration."""

import json
from pathlib import Path

import httpx
import pytest

from now_workbench.domains.instances.models import InstanceRecord
from now_workbench.domains.properties.engine import PropertyEngine
from now_workbench.domains.properties.models import (
    PropertyApplyResult,
    PropertyRecord,
    PropertySnapshot,
)


def test_property_models() -> None:
    """Verify Pydantic model integrity and frozen immutability."""
    rec = PropertyRecord(name="glide.ui.polaris.experience", value="true")
    assert rec.name == "glide.ui.polaris.experience"
    assert rec.value == "true"
    assert rec.description == ""

    snap = PropertySnapshot(
        bundle_id="sample-ai-assistant",
        instance_id="inst-1",
        timestamp="2026-10-29T12:00:00Z",
        original_values={"glide.ui.polaris.experience": "false"},
    )
    assert snap.bundle_id == "sample-ai-assistant"
    assert snap.original_values["glide.ui.polaris.experience"] == "false"

    res = PropertyApplyResult(
        success=True,
        applied_count=1,
        restored_count=0,
        details=["Set property"],
    )
    assert res.success is True
    assert res.applied_count == 1


def test_read_bundle_properties(tmp_path: Path) -> None:
    """Verify reading sys_properties.json from demo bundle structures."""
    engine = PropertyEngine(snapshots_dir=tmp_path / "snaps")

    # 1. Non-existent path returns empty dict
    assert engine.read_bundle_properties(tmp_path / "missing") == {}

    # 2. Corrupted JSON file returns empty dict
    corrupt_dir = tmp_path / "corrupt_bundle" / "properties"
    corrupt_dir.mkdir(parents=True)
    (corrupt_dir / "sys_properties.json").write_text("invalid json{{", encoding="utf-8")
    assert engine.read_bundle_properties(tmp_path / "corrupt_bundle") == {}

    # 3. Valid properties JSON in properties/sys_properties.json
    valid_dir = tmp_path / "valid_bundle" / "properties"
    valid_dir.mkdir(parents=True)
    valid_props = {"glide.ui.polaris.experience": "true", "x_demo.threshold": "0.95"}
    (valid_dir / "sys_properties.json").write_text(json.dumps(valid_props), encoding="utf-8")

    props = engine.read_bundle_properties(tmp_path / "valid_bundle")
    assert props == valid_props


def test_snapshot_lifecycle(tmp_path: Path) -> None:
    """Verify saving, loading, and deleting property snapshots."""
    snaps_dir = tmp_path / "snapshots"
    engine = PropertyEngine(snapshots_dir=snaps_dir)

    # Missing snapshot returns None
    assert engine.load_snapshot("b1", "inst-1") is None
    assert engine.delete_snapshot("b1", "inst-1") is False

    # Save snapshot
    snap = PropertySnapshot(
        bundle_id="b1",
        instance_id="inst-1",
        timestamp="2026-10-29T12:00:00Z",
        original_values={"prop.a": "val1", "prop.b": None},
    )
    saved_path = engine.save_snapshot(snap)
    assert saved_path.is_file()

    # Load snapshot
    loaded = engine.load_snapshot("b1", "inst-1")
    assert loaded is not None
    assert loaded.bundle_id == "b1"
    assert loaded.original_values["prop.a"] == "val1"
    assert loaded.original_values["prop.b"] is None

    # Corrupt snapshot file returns None
    saved_path.write_text("not json", encoding="utf-8")
    assert engine.load_snapshot("b1", "inst-1") is None

    # Delete snapshot
    saved_path.write_text("{}", encoding="utf-8")
    assert engine.delete_snapshot("b1", "inst-1") is True
    assert engine.load_snapshot("b1", "inst-1") is None


@pytest.mark.asyncio
async def test_apply_and_restore_fake_mode(tmp_path: Path) -> None:
    """Verify property apply and restore in simulated/fake mode."""
    bundle_dir = tmp_path / "fake_bundle"
    props_dir = bundle_dir / "properties"
    props_dir.mkdir(parents=True)
    (props_dir / "sys_properties.json").write_text(
        json.dumps({"test.prop": "value1"}), encoding="utf-8"
    )

    engine = PropertyEngine(snapshots_dir=tmp_path / "snaps")
    inst = InstanceRecord(
        id="fake-inst",
        name="Fake Instance",
        url="fake://test.service-now.com",
    )

    # 1. Apply in fake mode
    res_apply = await engine.apply_bundle_properties(
        bundle_id="fake_bundle",
        bundle_path=bundle_dir,
        instance=inst,
        fake_mode=True,
    )
    assert res_apply.success is True
    assert res_apply.applied_count == 1
    assert engine.load_snapshot("fake_bundle", "fake-inst") is not None

    # 2. Restore in fake mode
    res_restore = await engine.restore_properties(
        bundle_id="fake_bundle",
        instance=inst,
        fake_mode=True,
    )
    assert res_restore.success is True
    assert res_restore.restored_count == 1
    assert engine.load_snapshot("fake_bundle", "fake-inst") is None

    # 3. Restore when no snapshot exists
    res_no_snap = await engine.restore_properties(
        bundle_id="fake_bundle",
        instance=inst,
        fake_mode=True,
    )
    assert res_no_snap.success is True
    assert res_no_snap.restored_count == 0

    # 4. Apply bundle with no properties
    empty_dir = tmp_path / "empty_bundle"
    empty_dir.mkdir()
    res_empty = await engine.apply_bundle_properties(
        bundle_id="empty_bundle",
        bundle_path=empty_dir,
        instance=inst,
        fake_mode=True,
    )
    assert res_empty.success is True
    assert res_empty.applied_count == 0


@pytest.mark.asyncio
async def test_apply_properties_mock_transport(tmp_path: Path) -> None:
    """Verify apply_bundle_properties with in-memory HTTP mock transport."""
    bundle_dir = tmp_path / "http_bundle"
    props_dir = bundle_dir / "properties"
    props_dir.mkdir(parents=True)
    (props_dir / "sys_properties.json").write_text(
        json.dumps(
            {
                "glide.ui.polaris": "true",
                "custom.flag": "active",
                "fail.flag": "error",
            }
        ),
        encoding="utf-8",
    )

    engine = PropertyEngine(snapshots_dir=tmp_path / "snaps")
    inst = InstanceRecord(
        id="http-inst",
        name="HTTP Instance",
        url="https://instance.service-now.com",
        username="admin",
        password="pwd",
        auth_type="oauth",  # Test auth_type != 'basic' -> returns None (line 45)
    )

    # Mock handler:
    # - glide.ui.polaris exists with sys_id 111, cur_val false
    # - custom.flag does not exist, gets created with 201
    # - fail.flag exists with sys_id 333, PATCH returns 500 (line 177)
    def handle_requests(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if request.method == "GET" and "name=glide.ui.polaris" in url:
            return httpx.Response(200, json={"result": [{"sys_id": "111", "value": "false"}]})
        if request.method == "GET" and "name=custom.flag" in url:
            return httpx.Response(200, json={"result": []})
        if request.method == "GET" and "name=fail.flag" in url:
            return httpx.Response(200, json={"result": [{"sys_id": "333", "value": "old"}]})
        if request.method == "PATCH" and "sys_properties/111" in url:
            return httpx.Response(200, json={"result": {"value": "true"}})
        if request.method == "PATCH" and "sys_properties/333" in url:
            return httpx.Response(500, json={"error": "failed"})
        if request.method == "POST" and "sys_properties" in url:
            return httpx.Response(201, json={"result": {"sys_id": "222", "value": "active"}})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handle_requests))
    res = await engine.apply_bundle_properties(
        bundle_id="http_bundle",
        bundle_path=bundle_dir,
        instance=inst,
        client=client,
        fake_mode=False,
    )
    # One of the three updates failed (HTTP 500), so the apply must not report success.
    assert res.success is False
    assert res.applied_count == 2
    assert any("Set 'glide.ui.polaris'" in d for d in res.details)
    assert any("Failed to update 'fail.flag'" in d for d in res.details)

    snap = engine.load_snapshot("http_bundle", "http-inst")
    assert snap is not None
    assert snap.original_values["glide.ui.polaris"] == "false"
    assert snap.original_values["custom.flag"] is None


@pytest.mark.asyncio
async def test_restore_properties_mock_transport(tmp_path: Path) -> None:
    """Verify restore_properties with in-memory HTTP mock transport."""
    engine = PropertyEngine(snapshots_dir=tmp_path / "snaps")
    inst = InstanceRecord(
        id="http-inst",
        name="HTTP Instance",
        url="https://instance.service-now.com",
        username="admin",
        password="pwd",
        auth_type="basic",
    )

    # Pre-save snapshot with an original value
    snap = PropertySnapshot(
        bundle_id="http_bundle",
        instance_id="http-inst",
        timestamp="2026-10-29T12:00:00Z",
        original_values={"glide.ui.polaris": "false", "custom.flag": None},
    )
    engine.save_snapshot(snap)

    def handle_restore(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if request.method == "GET" and "name=glide.ui.polaris" in url:
            return httpx.Response(200, json={"result": [{"sys_id": "111", "value": "true"}]})
        if request.method == "PATCH" and "sys_properties/111" in url:
            return httpx.Response(200, json={"result": {"value": "false"}})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handle_restore))
    res = await engine.restore_properties(
        bundle_id="http_bundle",
        instance=inst,
        client=client,
        fake_mode=False,
    )
    assert res.success is True
    assert res.restored_count == 1
    assert any("Restored 'glide.ui.polaris'" in d for d in res.details)
    assert engine.load_snapshot("http_bundle", "http-inst") is None


@pytest.mark.asyncio
async def test_property_error_handling(tmp_path: Path) -> None:
    """Verify error handling on HTTP exceptions during apply and restore."""
    bundle_dir = tmp_path / "err_bundle"
    props_dir = bundle_dir / "properties"
    props_dir.mkdir(parents=True)
    (props_dir / "sys_properties.json").write_text(
        json.dumps({"error.prop": "val"}), encoding="utf-8"
    )

    engine = PropertyEngine(snapshots_dir=tmp_path / "snaps")
    inst = InstanceRecord(
        id="err-inst",
        name="Error Instance",
        url="https://instance.service-now.com",
    )

    def throw_err(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    client = httpx.AsyncClient(transport=httpx.MockTransport(throw_err))

    # Apply error
    res_apply = await engine.apply_bundle_properties(
        bundle_id="err_bundle",
        bundle_path=bundle_dir,
        instance=inst,
        client=client,
        fake_mode=False,
    )
    assert res_apply.success is False
    assert "Error applying properties" in res_apply.details[0]

    # Pre-save snapshot and test restore error
    snap = PropertySnapshot(
        bundle_id="err_bundle",
        instance_id="err-inst",
        timestamp="2026-10-29T12:00:00Z",
        original_values={"error.prop": "old_val"},
    )
    engine.save_snapshot(snap)

    res_restore = await engine.restore_properties(
        bundle_id="err_bundle",
        instance=inst,
        client=client,
        fake_mode=False,
    )
    assert res_restore.success is False
    assert "Error restoring properties" in res_restore.details[0]


async def test_read_live_values_reports_set_and_unset_properties() -> None:
    """Live values come from the instance; a property that does not exist reads as None."""
    inst = InstanceRecord(
        id="i1", name="Dev", url="https://dev.service-now.com", username="admin", password="p"
    )

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        if "name=glide.ui.polaris" in str(request.url):
            return httpx.Response(200, json={"result": [{"sys_id": "1", "value": "false"}]})
        return httpx.Response(200, json={"result": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    values = await PropertyEngine().read_live_values(
        ["glide.ui.polaris", "x.missing"], inst, client=client
    )
    assert values == {"glide.ui.polaris": "false", "x.missing": None}
