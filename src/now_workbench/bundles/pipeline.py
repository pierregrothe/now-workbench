"""End-to-end Demonstration Pipeline Engine:
Evaluation, module setup, seed, testing, and video proof.
"""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from now_workbench.bundles.manager import BundleManager
from now_workbench.capture.engine import PlaywrightCaptureEngine
from now_workbench.capture.models import CaptureArtifact, CaptureRequest
from now_workbench.db.models import InstanceRecord, SeedOperationRecord
from now_workbench.db.repository import DatabaseRepository
from now_workbench.plugins.manager import PluginManager
from now_workbench.plugins.models import PluginRecord
from now_workbench.properties.engine import PropertyEngine
from now_workbench.runbooks.engine import RunbookEngine
from now_workbench.runbooks.models import RunbookTestResult
from now_workbench.sdk.runner import NowSdkRunner
from now_workbench.seed.engine import SeedEngine


class DemoEvaluationResult(BaseModel):
    """Assessment of all requirements needed to run a demo bundle against an instance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_id: str
    instance_id: str
    instance_name: str
    sn_release: str
    required_plugins: list[str]
    missing_plugins: list[str]
    installed_plugins: list[str]
    system_properties_count: int
    seed_records_count: int
    target_tables: list[str]
    walkthrough_stages_count: int
    is_ready: bool


class DemoPipelineSummary(BaseModel):
    """Summary of executing the complete demonstration proof pipeline."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_id: str
    instance_name: str
    installed_modules: list[str] = Field(default_factory=list)
    applied_properties_count: int = 0
    seeded_records_count: int = 0
    tested_stages_count: int = 0
    test_passed: bool = True
    video_proof_url: str = ""
    video_proof_filename: str = ""
    status: str = "success"
    message: str = ""


class DemoPipelineEngine:
    """Orchestrates prerequisites evaluation, plugin installation, properties,
    seeding, testing, and proof capture.
    """

    def __init__(self, bundles_dir: Path, repo: DatabaseRepository) -> None:
        self.bundles_dir = bundles_dir
        self.repo = repo
        self.bundle_manager = BundleManager(storage_dir=bundles_dir)
        self.plugin_manager = PluginManager(repo=repo)
        self.prop_engine = PropertyEngine()
        self.runbook_engine = RunbookEngine()
        self.capture_engine = PlaywrightCaptureEngine(bundles_dir=bundles_dir)

    def _get_bundle_path(self, bundle_id: str) -> Path:
        path = self.bundles_dir / bundle_id
        if not path.is_dir():
            raise FileNotFoundError(f"Demo bundle '{bundle_id}' not found in {self.bundles_dir}")
        return path

    def evaluate_bundle(
        self,
        bundle_id: str,
        instance: InstanceRecord,
        fake_mode: bool = False,
    ) -> DemoEvaluationResult:
        """Evaluate required plugins, configurations, and data for a demo bundle."""
        bundle_path = self._get_bundle_path(bundle_id)
        info = self.bundle_manager.inspect_bundle(bundle_path)

        plugin_eval = self.plugin_manager.evaluate_plugins(
            instance=instance,
            required_plugins=info.manifest.required_plugins,
            fake_mode=fake_mode,
        )

        props = self.prop_engine.read_bundle_properties(bundle_path)

        seed_count = 0
        target_tables: set[str] = set()
        for seed_file in bundle_path.glob("seed/*.json"):
            try:
                raw = json.loads(seed_file.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    seed_count += len(raw)
                    for item in raw:
                        if isinstance(item, dict) and "table" in item:
                            target_tables.add(item["table"])
            except Exception:
                pass

        guide = self.runbook_engine.load_runbook(bundle_path, bundle_id=bundle_id)
        stages_count = len(guide.stages) if guide else 0

        is_ready = plugin_eval.all_satisfied

        return DemoEvaluationResult(
            bundle_id=bundle_id,
            instance_id=instance.id,
            instance_name=instance.name,
            sn_release=info.manifest.sn_release,
            required_plugins=info.manifest.required_plugins,
            missing_plugins=plugin_eval.missing,
            installed_plugins=plugin_eval.installed,
            system_properties_count=len(props),
            seed_records_count=seed_count,
            target_tables=sorted(target_tables),
            walkthrough_stages_count=stages_count,
            is_ready=is_ready,
        )

    def install_required_modules(
        self,
        bundle_id: str,
        instance: InstanceRecord,
        fake_mode: bool = False,
    ) -> list[PluginRecord]:
        """Install or activate all missing plugins/modules required by the demo."""
        bundle_path = self._get_bundle_path(bundle_id)
        info = self.bundle_manager.inspect_bundle(bundle_path)
        records, _ = self.plugin_manager.install_required_plugins(
            instance=instance,
            required_plugins=info.manifest.required_plugins,
            fake_mode=fake_mode,
        )
        return records

    async def configure_properties(
        self,
        bundle_id: str,
        instance: InstanceRecord,
        fake_mode: bool = False,
    ) -> dict[str, str]:
        """Apply the demo bundle system properties with snapshot backup."""
        bundle_path = self._get_bundle_path(bundle_id)
        props = self.prop_engine.read_bundle_properties(bundle_path)
        await self.prop_engine.apply_bundle_properties(
            bundle_id=bundle_id,
            bundle_path=bundle_path,
            instance=instance,
            fake_mode=fake_mode,
        )
        return props

    async def deploy_and_seed(
        self,
        bundle_id: str,
        instance: InstanceRecord,
        fake_mode: bool = False,
    ) -> SeedOperationRecord:
        """Deploy Fluent SDK application metadata and seed demo records."""
        bundle_path = self._get_bundle_path(bundle_id)

        # Deploy Fluent SDK metadata
        runner = NowSdkRunner(fake_mode=fake_mode)
        await runner.deploy(
            project_dir=bundle_path,
            instance_url=instance.url,
            username=instance.username,
            password=instance.password,
        )

        # Seed demonstration records
        seed_engine = SeedEngine(repository=self.repo, fake_mode=fake_mode)
        return await seed_engine.load_and_seed(
            bundle_id=bundle_id,
            bundle_path=bundle_path,
            instance_id=instance.id,
        )

    async def test_demo_script(
        self,
        bundle_id: str,
        instance: InstanceRecord,
        fake_mode: bool = False,
    ) -> RunbookTestResult:
        """Test all walkthrough runbook stages against the instance."""
        bundle_path = self._get_bundle_path(bundle_id)
        guide = self.runbook_engine.load_runbook(bundle_path, bundle_id=bundle_id)
        if not guide or not guide.stages:
            return RunbookTestResult(
                bundle_id=bundle_id,
                instance_name=instance.name,
                total_stages=0,
                passed_stages=0,
                all_passed=True,
                stages=[],
            )
        return await self.runbook_engine.test_runbook(guide, instance, fake_mode=fake_mode)

    async def record_video_proof(
        self,
        bundle_id: str,
        instance: InstanceRecord,
        caption: str = "Demonstration execution proof",
        target_path: str = "/incident_list.do",
        fake_mode: bool = False,
    ) -> CaptureArtifact:
        """Capture a video recording of the demo execution."""
        req = CaptureRequest(
            bundle_id=bundle_id,
            target_path=target_path,
            media_type="video",
            label=caption,
            fake_mode=fake_mode,
        )
        return await self.capture_engine.capture(
            req=req,
            instance_url=instance.url,
            username=instance.username,
            password=instance.password,
        )

    async def run_full_pipeline(
        self,
        bundle_id: str,
        instance: InstanceRecord,
        fake_mode: bool = False,
        record_video: bool = True,
    ) -> DemoPipelineSummary:
        """Execute the full end-to-end demo lifecycle and record video proof."""
        # 1. Evaluate & install modules
        installed_plugins = self.install_required_modules(bundle_id, instance, fake_mode=fake_mode)

        # 2. Configure properties
        applied_props = await self.configure_properties(bundle_id, instance, fake_mode=fake_mode)

        # 3. Deploy & seed demo records
        seed_result = await self.deploy_and_seed(bundle_id, instance, fake_mode=fake_mode)

        # 4. Test demo script runbook stages
        test_result = await self.test_demo_script(bundle_id, instance, fake_mode=fake_mode)

        # 5. Record video proof
        video_url = ""
        video_filename = ""
        if record_video:
            proof = await self.record_video_proof(
                bundle_id=bundle_id,
                instance=instance,
                caption=f"Verified Demo Execution Proof - {bundle_id}",
                fake_mode=fake_mode,
            )
            video_url = proof.url
            video_filename = proof.filename

        n_inst = len(installed_plugins)
        n_props = len(applied_props)
        n_rec = len(seed_result.created_records)
        stg_pass = test_result.passed_stages
        stg_tot = test_result.total_stages
        msg = (
            f"Successfully executed demo pipeline for '{bundle_id}' on {instance.name}: "
            f"{n_inst} modules activated, {n_props} properties configured, "
            f"{n_rec} records seeded, {stg_pass}/{stg_tot} stages verified. "
            f"Video proof recorded: {video_filename}"
        )

        return DemoPipelineSummary(
            bundle_id=bundle_id,
            instance_name=instance.name,
            installed_modules=[p.plugin_id for p in installed_plugins],
            applied_properties_count=len(applied_props),
            seeded_records_count=n_rec,
            tested_stages_count=test_result.total_stages,
            test_passed=test_result.all_passed,
            video_proof_url=video_url,
            video_proof_filename=video_filename,
            status="success" if test_result.all_passed else "partial",
            message=msg,
        )
