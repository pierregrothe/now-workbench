# tests/test_deepfix_property_apply.py
# Regression tests: apply_bundle_properties must report per-property failures
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for PropertyEngine.apply_bundle_properties failure reporting."""

import json
from pathlib import Path

import httpx

from now_workbench.db.models import InstanceRecord
from now_workbench.properties.engine import PropertyEngine


def _handler(request: httpx.Request) -> httpx.Response:
    if request.method == "GET":
        name = request.url.params["sysparm_query"].removeprefix("name=")
        return httpx.Response(200, json={"result": [{"sys_id": f"id_{name}", "value": "old"}]})
    if request.url.path.endswith("id_bad"):
        return httpx.Response(500, json={})
    return httpx.Response(200, json={})


def _setup(tmp_path: Path, props: dict[str, str]) -> tuple[PropertyEngine, Path, InstanceRecord]:
    bundle = tmp_path / "bundle"
    (bundle / "properties").mkdir(parents=True)
    (bundle / "properties" / "sys_properties.json").write_text(json.dumps(props))
    engine = PropertyEngine(snapshots_dir=tmp_path / "snaps")
    inst = InstanceRecord(id="i1", name="dev", url="https://dev.example.com")
    return engine, bundle, inst


async def test_apply_bundle_properties_partial_failure_reports_failure(tmp_path: Path) -> None:
    engine, bundle, inst = _setup(tmp_path, {"good": "1", "bad": "2"})
    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    result = await engine.apply_bundle_properties("b1", bundle, inst, client=client)
    assert result.success is False
    assert result.applied_count == 1
    assert "Failed to update 'bad'" in result.details
    assert "Set 'good' = '1'" in result.details


async def test_apply_bundle_properties_all_ok_reports_success(tmp_path: Path) -> None:
    engine, bundle, inst = _setup(tmp_path, {"good": "1"})
    client = httpx.AsyncClient(transport=httpx.MockTransport(_handler))
    result = await engine.apply_bundle_properties("b1", bundle, inst, client=client)
    assert result.success is True
    assert result.applied_count == 1
