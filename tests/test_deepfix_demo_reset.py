# tests/test_deepfix_demo_reset.py
# Regression tests: demo reset must not report success when seed rollback failed
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for the unified demo reset endpoint error propagation."""

import pytest
from fastapi.testclient import TestClient

from now_workbench.api import demos
from now_workbench.api.app import create_app
from now_workbench.db.models import SeedOperationRecord, SeedRecordItem
from now_workbench.db.repos.instances import InstanceRepository
from now_workbench.db.repos.seeds import SeedRepository
from now_workbench.db.session import db_session


class _FakeSeedEngine:
    """In-memory SeedEngine stand-in whose rollback reports one failed delete."""

    def __init__(self, conn: object, fake_mode: bool = False) -> None:
        self.errors = ["Could not delete incident/abc"]

    async def rollback(self, operation_id: str) -> tuple[int, list[str]]:
        return 2, self.errors


def _record_completed_op() -> None:
    with db_session() as conn:
        inst = InstanceRepository(conn).get_default_instance()
        assert inst is not None
        SeedRepository(conn).record_seed_operation(
            SeedOperationRecord(
                id="op-reset-fail",
                bundle_id="sample-ai-assistant",
                instance_id=inst.id,
                created_records=[SeedRecordItem(table="incident", sys_id="abc")],
            )
        )


def test_reset_demo_rollback_errors_report_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed seed delete makes the reset response unsuccessful and lists the error."""
    _record_completed_op()
    monkeypatch.setattr(demos, "SeedEngine", _FakeSeedEngine)
    client = TestClient(create_app())

    resp = client.post("/api/demos/sample-ai-assistant/reset", json={"fake_mode": True})

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["errors"] == ["Could not delete incident/abc"]
    assert data["seed_records_rolled_back"] == 2


def test_reset_demo_no_errors_reports_success() -> None:
    """With nothing to roll back the reset succeeds with an empty error list."""
    client = TestClient(create_app())

    resp = client.post("/api/demos/sample-ai-assistant/reset", json={"fake_mode": True})

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["errors"] == []
