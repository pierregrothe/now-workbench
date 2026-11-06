# tests/test_deepfix_pipeline_results.py
# Regression tests: the demo pipeline must not report success when deploy or properties fail
# Author: Pierre Grothe
# Date: 2026-11-06

from pathlib import Path

import pytest

from now_workbench.bundles import pipeline as pipeline_mod
from now_workbench.bundles.pipeline import DemoPipelineEngine, PipelineStepError
from now_workbench.db import InstanceCreate, InstanceProfile, db_session
from now_workbench.properties.engine import PropertyEngine
from now_workbench.properties.models import PropertyApplyResult
from now_workbench.sdk.runner import SdkExecutionResult
from now_workbench.synthesizer.engine import UseCaseSynthesizer
from now_workbench.synthesizer.models import UseCaseSynthesisRequest


class _FailingRunner:
    def __init__(self, fake_mode: bool = False) -> None:
        self.fake_mode = fake_mode

    async def deploy(self, **_kwargs: object) -> SdkExecutionResult:
        return SdkExecutionResult(command="deploy", exit_code=2, output="boom", success=False)


class _FailingPropEngine(PropertyEngine):
    async def apply_bundle_properties(self, **_kwargs: object) -> PropertyApplyResult:
        return PropertyApplyResult(success=False, applied_count=0, details=["Failed to update 'x'"])


def _setup(tmp_path: Path):
    bundles_dir = tmp_path / "bundles"
    bundles_dir.mkdir()
    result = UseCaseSynthesizer(bundles_dir=bundles_dir).synthesize(
        UseCaseSynthesisRequest(
            use_case="Automated incident triage using Now Assist AI",
            customer_name="Acme",
            industry="Healthcare",
            sn_release="Zurich",
            primary_color="#0066cc",
        )
    )
    # Make it a Fluent SDK project so the pipeline attempts the deploy step.
    (bundles_dir / result.bundle_id / "package.json").write_text("{}", encoding="utf-8")
    return bundles_dir, result.bundle_id


@pytest.mark.asyncio
async def test_deploy_and_seed_deploy_failure_raises(tmp_path: Path, monkeypatch):
    bundles_dir, bundle_id = _setup(tmp_path)
    monkeypatch.setattr(pipeline_mod, "NowSdkRunner", _FailingRunner)
    with db_session(tmp_path / "t.db") as repo:
        inst = repo.add_instance(
            InstanceCreate(id="i1", name="I1", url="https://a.service-now.com", is_default=True)
        )
        engine = DemoPipelineEngine(bundles_dir=bundles_dir, repo=repo)
        with pytest.raises(PipelineStepError, match="exit code 2"):
            await engine.deploy_and_seed(bundle_id, inst, fake_mode=True)


@pytest.mark.asyncio
async def test_run_full_pipeline_deploy_failure_reports_failed(tmp_path: Path, monkeypatch):
    bundles_dir, bundle_id = _setup(tmp_path)
    monkeypatch.setattr(pipeline_mod, "NowSdkRunner", _FailingRunner)
    with db_session(tmp_path / "t.db") as repo:
        repo.add_instance(
            InstanceCreate(id="i1", name="I1", url="https://a.service-now.com", is_default=True)
        )
        repo.save_instance_profile(InstanceProfile(instance_id="i1", release="Zurich"))
        inst = repo.get_instance("i1")
        assert inst is not None
        engine = DemoPipelineEngine(bundles_dir=bundles_dir, repo=repo)
        summary = await engine.run_full_pipeline(
            bundle_id, inst, fake_mode=True, record_video=False
        )
        assert summary.status == "failed"
        assert summary.seeded_records_count == 0
        assert "SDK deploy failed" in summary.message


@pytest.mark.asyncio
async def test_run_full_pipeline_property_failure_reports_failed(tmp_path: Path):
    bundles_dir, bundle_id = _setup(tmp_path)
    with db_session(tmp_path / "t.db") as repo:
        repo.add_instance(
            InstanceCreate(id="i1", name="I1", url="https://a.service-now.com", is_default=True)
        )
        repo.save_instance_profile(InstanceProfile(instance_id="i1", release="Zurich"))
        inst = repo.get_instance("i1")
        assert inst is not None
        engine = DemoPipelineEngine(bundles_dir=bundles_dir, repo=repo)
        engine.prop_engine = _FailingPropEngine()
        summary = await engine.run_full_pipeline(
            bundle_id, inst, fake_mode=True, record_video=False
        )
        assert summary.status == "failed"
        assert "Failed to update 'x'" in summary.message


@pytest.mark.asyncio
async def test_deploy_and_seed_without_sdk_project_on_fake_instance_simulates_deploy(
    tmp_path: Path, monkeypatch
):
    """A bundle without package.json on a simulated instance is seeded; deploy is simulated."""
    bundles_dir, bundle_id = _setup(tmp_path)
    (bundles_dir / bundle_id / "package.json").unlink()
    monkeypatch.setattr(pipeline_mod, "NowSdkRunner", _FailingRunner)
    with db_session(tmp_path / "t.db") as repo:
        inst = repo.add_instance(
            InstanceCreate(id="i1", name="I1", url="https://a.service-now.com", is_default=True)
        )
        engine = DemoPipelineEngine(bundles_dir=bundles_dir, repo=repo)
        seed, note, renames = await engine.deploy_and_seed(bundle_id, inst, fake_mode=True)
        assert seed.status == "completed"
        assert "simulated" in note
        assert renames == {}
