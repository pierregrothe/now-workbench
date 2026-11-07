# tests/test_fake_mode_safety.py
# One simulated-instance rule everywhere; nothing simulated reaches a real deploy (STORY-072).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests for the exported ``is_simulated`` predicate and every caller that relies on it.

No test contacts a network: the seed engine's record calls, the SDK runner, the capture engine
and the plugin query transport are replaced by in-memory recorders.
"""

import json
import shutil
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from now_workbench.domains.capture import CaptureFailedError, CaptureRequest
from now_workbench.domains.capture import engine as capture_engine_mod
from now_workbench.domains.demos import pipeline as pipeline_mod
from now_workbench.domains.demos.pipeline import DemoPipelineEngine
from now_workbench.domains.instances import InstanceCreate, InstanceRepository, is_simulated
from now_workbench.domains.plugins.manager import PluginManager
from now_workbench.domains.seed import SeedEngine
from now_workbench.interfaces.ai.tools.base import ToolContext, execute_tool
from now_workbench.interfaces.api.app import create_app
from now_workbench.platform.db.session import db_session
from now_workbench.platform.sdk.runner import SdkExecutionResult

REPO = Path(__file__).resolve().parents[1]
REAL_URL = "https://real.service-now.com"
HTTP_FAKE_URL = "http://fake-dev.service-now.com"


def _instance(inst_id: str, url: str) -> None:
    with db_session() as conn:
        InstanceRepository(conn).add_instance(
            InstanceCreate(id=inst_id, name=inst_id, url=url, password="p")
        )


def _record_posts(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Replace the seed engine's live POST with a recorder that refuses to post."""
    posted: list[str] = []

    async def no_post(self: SeedEngine, client: object, inst: object, table: str, f: object) -> str:
        if self.fake_mode:
            return "fake_sys_recorded"
        posted.append(table)
        raise RuntimeError("a live POST was attempted")

    monkeypatch.setattr(SeedEngine, "_post_record", no_post)
    return posted


def _record_captures(monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    """Replace the capture engine with a recorder of the fake_mode it was asked for."""
    seen: list[bool] = []

    async def capture(self: object, req: CaptureRequest, **_kwargs: object) -> None:
        seen.append(req.fake_mode)
        raise CaptureFailedError("recorded")

    monkeypatch.setattr(capture_engine_mod.PlaywrightCaptureEngine, "capture", capture)
    return seen


# -- AC1: one exported predicate ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "fake_mode", "expected"),
    [
        ("fake://dev.service-now.com", False, True),
        (HTTP_FAKE_URL, False, True),
        (REAL_URL, True, True),
        (REAL_URL, False, False),
    ],
)
def test_is_simulated_is_exported_from_the_instances_root(
    url: str, fake_mode: bool, expected: bool
) -> None:
    """The predicate is on the public root and covers both fake URL forms and the flag."""
    _instance("x", url)
    with db_session() as conn:
        inst = InstanceRepository(conn).get_instance("x")
    assert inst is not None
    assert is_simulated(inst, fake_mode) is expected


def test_otto_seed_treats_http_fake_as_simulated(monkeypatch: pytest.MonkeyPatch) -> None:
    """Otto's seed tool simulates on an ``http://fake`` instance even with fake mode off."""
    posted = _record_posts(monkeypatch)
    _instance("hf", HTTP_FAKE_URL)
    with db_session() as conn:
        res = execute_tool(
            ToolContext(conn=conn),
            "seed_bundle",
            {"bundle_id": "sample-ai-assistant", "instance": "hf"},
        )
    assert posted == []
    assert res.ok and res.data["records"] == 2


@pytest.mark.parametrize("tool", ["verify_seed_operation", "rollback_seed"])
def test_otto_seed_operation_tools_treat_http_fake_as_simulated(
    tool: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify and roll back a seed run on an ``http://fake`` instance in simulation."""
    _instance("hf", HTTP_FAKE_URL)
    seen: list[bool] = []

    async def verify(self: SeedEngine, operation_id: str) -> list[Any]:
        seen.append(self.fake_mode)
        return []

    async def rollback(self: SeedEngine, operation_id: str) -> tuple[int, list[str]]:
        seen.append(self.fake_mode)
        return 0, []

    with db_session() as conn:
        seeded = execute_tool(
            ToolContext(conn=conn, fake_mode=True),
            "seed_bundle",
            {"bundle_id": "sample-ai-assistant", "instance": "hf"},
        )
        monkeypatch.setattr(SeedEngine, "verify", verify)
        monkeypatch.setattr(SeedEngine, "rollback", rollback)
        execute_tool(
            ToolContext(conn=conn),
            tool,
            {"operation_id": seeded.data["operation_id"]},
            confirmed=True,
        )
    assert seen == [True]


def test_otto_seed_operation_tool_on_unknown_operation_uses_the_context_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no recorded operation, only the context's fake mode decides."""
    seen: list[bool] = []

    async def verify(self: SeedEngine, operation_id: str) -> list[Any]:
        seen.append(self.fake_mode)
        return []

    monkeypatch.setattr(SeedEngine, "verify", verify)
    with db_session() as conn:
        execute_tool(ToolContext(conn=conn), "verify_seed_operation", {"operation_id": "seed-x"})
    assert seen == [False]


def test_plugin_checks_treat_http_fake_as_simulated() -> None:
    """Plugin evaluation and install never query an ``http://fake`` instance."""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, json={"result": []})

    _instance("hf", HTTP_FAKE_URL)
    with db_session() as conn:
        inst = InstanceRepository(conn).get_instance("hf")
        assert inst is not None
        manager = PluginManager(conn, transport=httpx.MockTransport(handler))
        result = manager.evaluate_plugins(inst, ["com.snc.incident"], fake_mode=False)
        ok, _msg = manager.install_plugin(inst, "com.snc.incident", fake_mode=False)
    assert calls == []
    assert result.missing == ["com.snc.incident"] and ok


def test_capture_api_simulates_on_a_simulated_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    """The capture endpoint asks for a placeholder when the instance itself is fake."""
    seen = _record_captures(monkeypatch)
    res = TestClient(create_app()).post(
        "/api/demos/sample-ai-assistant/captures", json={"bundle_id": "sample-ai-assistant"}
    )
    assert res.status_code == 502
    assert seen == [True]


def test_otto_capture_simulates_on_a_simulated_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    """Otto's capture tool asks for a placeholder when the instance itself is fake."""
    seen = _record_captures(monkeypatch)
    with db_session() as conn:
        execute_tool(ToolContext(conn=conn), "capture_media", {"bundle_id": "sample-ai-assistant"})
    assert seen == [True]


async def test_pipeline_video_proof_simulates_on_a_simulated_instance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pipeline's video proof asks for a placeholder when the instance is fake."""
    seen = _record_captures(monkeypatch)
    with db_session(tmp_path / "t.db") as conn:
        inst = InstanceRepository(conn).add_instance(
            InstanceCreate(id="f", name="Fake", url="fake://f.service-now.com", password="p")
        )
        engine = DemoPipelineEngine(bundles_dir=REPO / "bundles", conn=conn)
        with pytest.raises(CaptureFailedError):
            await engine.record_video_proof("sample-ai-assistant", inst, fake_mode=False)
    assert seen == [True]


# -- AC2: no real SDK deploy for a simulated instance -----------------------------------------


async def test_deploy_and_seed_sdk_project_on_simulated_instance_never_deploys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A package.json bundle on a ``fake://`` instance with fake mode off is simulated."""
    bundles = tmp_path / "bundles"
    shutil.copytree(REPO / "bundles" / "hr-onboarding-ai", bundles / "b")
    (bundles / "b" / "package.json").write_text(json.dumps({"name": "b"}), encoding="utf-8")
    deploys: list[bool] = []

    class _RecordingRunner:
        def __init__(self, fake_mode: bool = False) -> None:
            self.fake_mode = fake_mode

        async def deploy(self, **kwargs: object) -> SdkExecutionResult:
            deploys.append(self.fake_mode)
            return SdkExecutionResult(command="deploy", exit_code=0, output="", success=True)

    monkeypatch.setattr(pipeline_mod, "NowSdkRunner", _RecordingRunner)
    posted = _record_posts(monkeypatch)
    with db_session(tmp_path / "t.db") as conn:
        inst = InstanceRepository(conn).add_instance(
            InstanceCreate(id="f", name="Fake", url="fake://f.service-now.com", password="p")
        )
        engine = DemoPipelineEngine(bundles_dir=bundles, conn=conn)
        seed, note, renames = await engine.deploy_and_seed("b", inst, fake_mode=False)
    assert deploys == []
    assert posted == []
    assert "simulated" in note and renames == {}
    assert seed.status == "completed"


# -- AC3: the seed API never takes less than the request flag, the preference or the URL -------


def test_seed_api_honours_the_sdk_fake_mode_preference(monkeypatch: pytest.MonkeyPatch) -> None:
    """With ``sdk_fake_mode`` on, a real instance is not posted to even without the flag."""
    posted = _record_posts(monkeypatch)
    _instance("real", REAL_URL)
    client = TestClient(create_app())
    assert client.put("/api/settings", json={"sdk_fake_mode": True}).status_code == 200
    res = client.post("/api/demos/sample-ai-assistant/seed", json={"instance_id": "real"})
    assert res.status_code == 200, res.text
    assert posted == []


def test_seed_api_simulates_on_a_simulated_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    """The default ``fake://`` instance is simulated even with no flag and no preference."""
    posted = _record_posts(monkeypatch)
    res = TestClient(create_app()).post("/api/demos/sample-ai-assistant/seed", json={})
    assert res.status_code == 200, res.text
    assert posted == []
    assert all(r["sys_id"].startswith("fake_sys") for r in res.json()["created_records"])


def test_seed_api_keeps_the_request_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """The request flag alone still simulates on a real instance."""
    posted = _record_posts(monkeypatch)
    _instance("real", REAL_URL)
    res = TestClient(create_app()).post(
        "/api/demos/sample-ai-assistant/seed", json={"instance_id": "real", "fake_mode": True}
    )
    assert res.status_code == 200, res.text
    assert posted == []


def test_seed_api_unknown_instance_is_a_400(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unknown instance still fails as before (there is no instance to judge)."""
    _record_posts(monkeypatch)
    res = TestClient(create_app()).post(
        "/api/demos/sample-ai-assistant/seed", json={"instance_id": "nope"}
    )
    assert res.status_code == 400


def test_seed_rollback_api_simulates_on_a_simulated_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rolling back a run on the ``fake://`` instance never sends a live DELETE."""
    client = TestClient(create_app())
    seeded = client.post("/api/demos/sample-ai-assistant/seed", json={"fake_mode": True})
    deleted: list[str] = []

    async def no_delete(self: SeedEngine, client: object, inst: object, t: str, s: str) -> bool:
        if self.fake_mode:
            return True
        deleted.append(s)
        raise RuntimeError("a live DELETE was attempted")

    monkeypatch.setattr(SeedEngine, "_delete_record", no_delete)
    res = client.post(f"/api/demos/seed/{seeded.json()['id']}/rollback")
    assert res.status_code == 200
    assert deleted == [] and res.json()["deleted_count"] == 2


def test_seed_rollback_api_unknown_operation_is_a_400() -> None:
    """An unknown operation still fails as before."""
    res = TestClient(create_app()).post("/api/demos/seed/seed-nope/rollback")
    assert res.status_code == 400
