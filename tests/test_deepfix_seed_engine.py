# tests/test_deepfix_seed_engine.py
# Regression tests for seed engine failure truthfulness and rollback status
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for SeedEngine partial-failure persistence, rollback status and payload errors."""

import json
import sqlite3
from pathlib import Path

import httpx
import pytest

from now_workbench.domains.instances.models import InstanceCreate
from now_workbench.domains.instances.repository import InstanceRepository
from now_workbench.domains.seed.engine import SeedEngine, SeedPayloadError
from now_workbench.domains.seed.models import SeedOperationRecord, SeedRecordItem
from now_workbench.domains.seed.repository import SeedRepository
from now_workbench.platform.db.session import init_db


def _repo() -> sqlite3.Connection:
    conn = init_db(":memory:")
    InstanceRepository(conn).add_instance(
        InstanceCreate(
            id="inst",
            name="Inst",
            url="https://inst.service-now.com",
            username="admin",
            password="pw",
            is_default=True,
        )
    )
    return conn


def _bundle(tmp_path: Path, count: int = 3) -> Path:
    seed_dir = tmp_path / "b" / "seed"
    seed_dir.mkdir(parents=True)
    items = [{"table": "incident", "fields": {"short_description": f"n{i}"}} for i in range(count)]
    (seed_dir / "01.json").write_text(json.dumps(items), encoding="utf-8")
    return tmp_path / "b"


def _transport(fail_post_at: int | None = None, fail_delete: bool = False) -> httpx.MockTransport:
    state = {"posts": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            state["posts"] += 1
            if state["posts"] == fail_post_at:
                return httpx.Response(500, text="boom")
            return httpx.Response(201, json={"result": {"sys_id": f"id{state['posts']}"}})
        if fail_delete:
            return httpx.Response(500, text="nope")
        return httpx.Response(204)

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_load_and_seed_mid_batch_failure_persists_created_records(tmp_path: Path) -> None:
    conn = _repo()
    engine = SeedEngine(conn, transport=_transport(fail_post_at=3))
    with pytest.raises(RuntimeError, match="failed after 2 record"):
        await engine.load_and_seed("b", _bundle(tmp_path))
    ops = SeedRepository(conn).list_seed_operations()
    assert len(ops) == 1
    assert ops[0].status == "failed"
    assert [r.sys_id for r in ops[0].created_records] == ["id1", "id2"]


@pytest.mark.asyncio
async def test_rollback_partial_failure_keeps_operation_retryable(tmp_path: Path) -> None:
    conn = _repo()
    seed_repo = SeedRepository(conn)
    op = await SeedEngine(conn, transport=_transport()).load_and_seed("b", _bundle(tmp_path))
    failing = SeedEngine(conn, transport=_transport(fail_delete=True))
    count, errors = await failing.rollback(op.id)
    assert count == 0
    assert len(errors) == 3
    saved = seed_repo.get_seed_operation(op.id)
    assert saved is not None
    assert saved.status == "rollback_failed"

    count, errors = await SeedEngine(conn, transport=_transport()).rollback(op.id)
    assert (count, errors) == (3, [])
    saved = seed_repo.get_seed_operation(op.id)
    assert saved is not None
    assert saved.status == "rolled_back"


@pytest.mark.asyncio
async def test_rollback_failed_seed_operation_marks_rolled_back(tmp_path: Path) -> None:
    conn = _repo()
    seed_repo = SeedRepository(conn)
    engine = SeedEngine(conn, transport=_transport(fail_post_at=2))
    with pytest.raises(RuntimeError):
        await engine.load_and_seed("b", _bundle(tmp_path))
    op_id = seed_repo.list_seed_operations()[0].id
    count, errors = await engine.rollback(op_id)
    assert (count, errors) == (1, [])
    saved = seed_repo.get_seed_operation(op_id)
    assert saved is not None
    assert saved.status == "rolled_back"


@pytest.mark.asyncio
async def test_load_and_seed_malformed_seed_file_raises_naming_file(tmp_path: Path) -> None:
    conn = _repo()
    bundle = _bundle(tmp_path)
    (bundle / "seed" / "02_bad.json").write_text("{not json", encoding="utf-8")
    engine = SeedEngine(conn, fake_mode=True)
    with pytest.raises(SeedPayloadError, match="02_bad.json"):
        await engine.load_and_seed("b", bundle)
    assert SeedRepository(conn).list_seed_operations() == []


async def test_verify_reports_present_and_missing_records() -> None:
    """verify() looks each created record up by sys_id and says which are gone."""
    conn = init_db(":memory:")
    InstanceRepository(conn).add_instance(
        InstanceCreate(id="i1", name="Dev", url="https://dev.service-now.com", password="p")
    )
    SeedRepository(conn).record_seed_operation(
        SeedOperationRecord(
            id="seed-1",
            bundle_id="b",
            instance_id="i1",
            created_records=[
                SeedRecordItem(table="incident", sys_id="aaa"),
                SeedRecordItem(table="incident", sys_id="bbb"),
            ],
        )
    )

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/aaa"):
            return httpx.Response(200, json={"result": {"sys_id": "aaa", "number": "INC1"}})
        return httpx.Response(404, json={"error": {}})

    engine = SeedEngine(conn=conn, transport=httpx.MockTransport(handler))
    checks = await engine.verify("seed-1")
    assert [(i.sys_id, ok, d) for i, ok, d in checks] == [
        ("aaa", True, "INC1"),
        ("bbb", False, "HTTP 404"),
    ]


async def test_load_and_seed_failure_keeps_the_reason() -> None:
    """A failed seed run stores why it failed for later diagnosis."""
    conn = init_db(":memory:")
    InstanceRepository(conn).add_instance(
        InstanceCreate(id="i1", name="Dev", url="https://dev.service-now.com", password="p")
    )
    bundle = Path(__file__).resolve().parents[1] / "bundles" / "sample-ai-assistant"
    transport = httpx.MockTransport(lambda req: httpx.Response(403, text="ACL denied"))
    engine = SeedEngine(conn=conn, transport=transport)
    with pytest.raises(RuntimeError):
        await engine.load_and_seed("sample-ai-assistant", bundle, instance_id="i1")
    op = SeedRepository(conn).list_seed_operations()[0]
    assert op.status == "failed"
    assert "HTTP 403" in op.error
