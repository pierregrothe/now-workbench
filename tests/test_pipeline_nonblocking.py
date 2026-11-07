# tests/test_pipeline_nonblocking.py
# The async demo pipeline runs its blocking plugin queries off the event loop (STORY-075).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests that ``run_full_pipeline`` keeps the event loop free during plugin queries."""

import asyncio
import time
from pathlib import Path

import httpx

from now_workbench.domains.demos import pipeline as pipeline_mod
from now_workbench.domains.demos.pipeline import DemoPipelineEngine
from now_workbench.domains.instances.models import InstanceCreate, InstanceProfile
from now_workbench.domains.instances.repository import InstanceRepository
from now_workbench.domains.plugins.manager import PluginManager
from now_workbench.domains.properties.engine import PropertyEngine
from now_workbench.domains.properties.models import PropertyApplyResult
from now_workbench.domains.synthesizer.engine import UseCaseSynthesizer
from now_workbench.domains.synthesizer.models import UseCaseSynthesisRequest
from now_workbench.platform.db.session import db_session
from now_workbench.platform.sdk.runner import SdkExecutionResult

_QUERY_S = 0.3


class _FailingRunner:
    def __init__(self, fake_mode: bool = False) -> None:
        self.fake_mode = fake_mode

    async def deploy(self, **_kwargs: object) -> SdkExecutionResult:
        return SdkExecutionResult(command="deploy", exit_code=2, output="boom", success=False)


class _OkPropEngine(PropertyEngine):
    async def apply_bundle_properties(self, **_kwargs: object) -> PropertyApplyResult:
        return PropertyApplyResult(success=True, applied_count=0, details=[])


async def test_plugin_queries_do_not_block_the_event_loop(tmp_path: Path, monkeypatch) -> None:
    """A concurrent task keeps ticking while a slow plugin query is in flight."""
    bundles_dir = tmp_path / "bundles"
    bundles_dir.mkdir()
    bundle_id = (
        UseCaseSynthesizer(bundles_dir=bundles_dir)
        .synthesize(
            UseCaseSynthesisRequest(
                use_case="Automated incident triage using Now Assist AI",
                customer_name="Acme",
                industry="Healthcare",
                sn_release="Zurich",
                primary_color="#0066cc",
            )
        )
        .bundle_id
    )
    (bundles_dir / bundle_id / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(pipeline_mod, "NowSdkRunner", _FailingRunner)

    windows: list[tuple[float, float]] = []

    def slow_instance(request: httpx.Request) -> httpx.Response:
        start = time.monotonic()
        time.sleep(_QUERY_S)  # a slow instance, as a sync transport sees it
        windows.append((start, time.monotonic()))
        plugin_id = request.url.params["sysparm_query"].removeprefix("id=")
        return httpx.Response(200, json={"result": [{"id": plugin_id, "active": "active"}]})

    ticks: list[float] = []
    done = asyncio.Event()

    async def ticker() -> None:
        while not done.is_set():
            ticks.append(time.monotonic())
            await asyncio.sleep(0.02)

    with db_session(tmp_path / "t.db") as conn:
        repo = InstanceRepository(conn)
        repo.add_instance(
            InstanceCreate(id="i1", name="I1", url="https://a.service-now.com", is_default=True)
        )
        repo.save_instance_profile(InstanceProfile(instance_id="i1", release="Zurich"))
        inst = repo.get_instance("i1")
        assert inst is not None
        engine = DemoPipelineEngine(bundles_dir=bundles_dir, conn=conn)
        engine.plugin_manager = PluginManager(conn, transport=httpx.MockTransport(slow_instance))
        engine.prop_engine = _OkPropEngine()

        tick_task = asyncio.create_task(ticker())
        await asyncio.sleep(0)
        summary = await engine.run_full_pipeline(bundle_id, inst, record_video=False)
        done.set()
        await tick_task

    assert summary.status == "failed"  # the faked deploy fails; plugins ran first
    assert windows, "the pipeline queried no plugin"
    for start, end in windows:
        inside = [t for t in ticks if start < t < end]
        assert len(inside) >= 3, f"event loop blocked for {end - start:.2f}s"
