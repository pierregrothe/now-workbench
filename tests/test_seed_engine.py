"""Tests for SeedEngine transactional seed record loading and rollback tracking."""

from pathlib import Path

import pytest

from now_workbench.db import InstanceCreate, init_db
from now_workbench.db.repos.instances import InstanceRepository
from now_workbench.db.repos.seeds import SeedRepository
from now_workbench.seed.engine import SeedEngine, SeedPayloadError


@pytest.mark.asyncio
async def test_seed_engine_lifecycle(tmp_path: Path) -> None:
    """Verify seed execution, audit tracking, and reverse rollback in fake mode."""
    conn = init_db(":memory:")

    # 1. Register test instance
    seed_repo = SeedRepository(conn)
    InstanceRepository(conn).add_instance(
        InstanceCreate(
            id="test-inst",
            name="Test Sandbox",
            url="https://testsandbox.service-now.com",
            username="admin",
            password="secret_password",
            is_default=True,
        )
    )

    # 2. Setup a sample bundle seed directory
    bundle_dir = tmp_path / "test-bundle"
    seed_dir = bundle_dir / "seed"
    seed_dir.mkdir(parents=True)
    seed_file = seed_dir / "01_incidents.json"
    seed_file.write_text(
        """
        [
            {"table": "incident", "fields": {"short_description": "First test incident"}},
            {"table": "incident", "fields": {"short_description": "Second test incident"}}
        ]
        """,
        encoding="utf-8",
    )

    engine = SeedEngine(conn=conn, fake_mode=True)

    # 3. Load and seed records
    op = await engine.load_and_seed("test-bundle", bundle_dir)
    assert op.bundle_id == "test-bundle"
    assert op.instance_id == "test-inst"
    assert op.status == "completed"
    assert len(op.created_records) == 2
    assert op.created_records[0].table == "incident"
    assert op.created_records[0].sys_id.startswith("fake_sys_")

    # 4. Verify persisted in SQLite
    saved_op = seed_repo.get_seed_operation(op.id)
    assert saved_op is not None
    assert saved_op.id == op.id
    assert len(saved_op.created_records) == 2

    # 5. Rollback operation
    deleted_count, errors = await engine.rollback(op.id)
    assert deleted_count == 2
    assert len(errors) == 0

    # 6. Verify status updated to rolled_back
    rolled_op = seed_repo.get_seed_operation(op.id)
    assert rolled_op is not None
    assert rolled_op.status == "rolled_back"

    # 7. Disallow double rollback
    with pytest.raises(ValueError, match="already been rolled back"):
        await engine.rollback(op.id)
    conn.close()


@pytest.mark.asyncio
async def test_seed_engine_missing_instance(tmp_path: Path) -> None:
    """Verify error handling when target instance cannot be resolved."""
    conn = init_db(":memory:")
    engine = SeedEngine(conn=conn, fake_mode=True)

    with pytest.raises(ValueError, match="No active default instance"):
        await engine.load_and_seed("bundle", tmp_path)
    conn.close()


@pytest.mark.asyncio
async def test_seed_engine_edge_cases_and_http_transport(tmp_path: Path) -> None:
    """Verify edge cases and Table API HTTP interactions using in-memory mock transport."""
    import httpx

    from now_workbench.db.models import InstanceRecord

    conn = init_db(":memory:")
    seed_repo = SeedRepository(conn)
    engine = SeedEngine(conn=conn, fake_mode=False)

    inst = InstanceRecord(
        id="mock-inst",
        name="Mock Instance",
        url="https://mock.service-now.com",
        username="admin",
        password="pwd",
        auth_type="basic",
        release="Zurich",
        is_default=True,
        status="authenticated",
    )

    # 1. Successful HTTP Table API post
    def mock_post_ok(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"result": {"sys_id": "real_sys_12345"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_post_ok)) as client:
        sys_id = await engine._post_record(client, inst, "incident", {"short_description": "test"})
        assert sys_id == "real_sys_12345"

    # 2. Failed HTTP Table API post (HTTP 500)
    def mock_post_fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_post_fail)) as client:
        with pytest.raises(RuntimeError, match="Failed to seed record"):
            await engine._post_record(client, inst, "incident", {})

    # 3. HTTP Table API post missing sys_id
    def mock_post_no_sys_id(request: httpx.Request) -> httpx.Response:
        return httpx.Response(201, json={"result": {}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_post_no_sys_id)) as client:
        with pytest.raises(RuntimeError, match="missing sys_id"):
            await engine._post_record(client, inst, "incident", {})

    # 4. Successful HTTP Table API delete
    def mock_del_ok(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_del_ok)) as client:
        ok = await engine._delete_record(client, inst, "incident", "real_sys_12345")
        assert ok is True

    # 5. HTTP 404 means the record is already gone: deleting it again is idempotent, so a
    # retry of a partially failed rollback can complete.
    def mock_del_gone(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_del_gone)) as client:
        ok = await engine._delete_record(client, inst, "incident", "real_sys_12345")
        assert ok is True

    # 5b. A real server error is a failed delete.
    def mock_del_fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_del_fail)) as client:
        ok = await engine._delete_record(client, inst, "incident", "real_sys_12345")
        assert ok is False

    # 6. Read seed payloads from non-existent directory
    assert engine._read_seed_payloads(tmp_path / "does-not-exist") == []

    # 7. A corrupted seed file is an error naming the file, never silently skipped
    # (a skipped file would leave the operation "completed" with missing data).
    corrupt_dir = tmp_path / "corrupt_seed"
    corrupt_dir.mkdir()
    (corrupt_dir / "bad.json").write_text("{not valid json", encoding="utf-8")
    with pytest.raises(SeedPayloadError, match="bad.json"):
        engine._read_seed_payloads(corrupt_dir)

    # 8. Load and seed empty directory raises ValueError
    empty_bundle = tmp_path / "empty-bundle"
    (empty_bundle / "seed").mkdir(parents=True)
    InstanceRepository(conn).add_instance(
        InstanceCreate(id="mock-inst", name="Mock", url="https://m.sn.com", is_default=True)
    )
    with pytest.raises(ValueError, match="No seed records found"):
        await engine.load_and_seed("empty", empty_bundle)

    # 9. Rollback non-existent operation raises ValueError
    with pytest.raises(ValueError, match="not found"):
        await engine.rollback("op-non-existent")

    # 10. Resolve unknown instance ID raises ValueError
    with pytest.raises(ValueError, match="not found in registry"):
        engine._resolve_instance("instance-404")

    # 11. Rollback failure records error in non-fake mode
    from now_workbench.db.models import SeedOperationRecord, SeedRecordItem

    fail_op = SeedOperationRecord(
        id="op-with-unreachable-record",
        bundle_id="b",
        instance_id="mock-inst",
        created_records=[SeedRecordItem(table="incident", sys_id="bad-sys-id")],
    )
    seed_repo.record_seed_operation(fail_op)

    # In-memory transport returning HTTP 500 for delete (a 404 would mean "already gone")
    import httpx

    def mock_delete_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"message": "Server error"}})

    mock_transport = httpx.MockTransport(mock_delete_handler)
    engine_404 = SeedEngine(conn=conn, fake_mode=False, transport=mock_transport)
    del_count, errs = await engine_404.rollback(fail_op.id)
    assert del_count == 0
    assert len(errs) == 1
    assert "Could not delete incident/bad-sys-id" in errs[0]

    # Target URL is unreachable in sandbox, triggering exception handler in rollback loop
    fail_op_unreachable = SeedOperationRecord(
        id="op-with-unreachable-exception",
        bundle_id="b",
        instance_id="mock-inst",
        created_records=[SeedRecordItem(table="incident", sys_id="bad-sys-id")],
    )
    seed_repo.record_seed_operation(fail_op_unreachable)
    del_count_err, errs_exc = await engine.rollback(fail_op_unreachable.id)
    assert del_count_err == 0
    assert len(errs_exc) == 1
    assert "bad-sys-id" in errs_exc[0]
    conn.close()
