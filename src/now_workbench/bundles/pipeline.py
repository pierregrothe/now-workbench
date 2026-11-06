"""End-to-end Demonstration Pipeline Engine:
Evaluation, module setup, seed, testing, and video proof.
"""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from now_workbench.bundles.manager import BundleManager
from now_workbench.capture.engine import CaptureFailedError, PlaywrightCaptureEngine
from now_workbench.capture.models import CaptureArtifact, CaptureRequest
from now_workbench.config.paths import safe_child
from now_workbench.config.settings import settings
from now_workbench.db.models import InstanceRecord, SeedOperationRecord
from now_workbench.db.repository import DatabaseRepository
from now_workbench.plugins.manager import PluginManager
from now_workbench.plugins.models import PluginRecord
from now_workbench.properties.engine import PropertyEngine
from now_workbench.properties.models import PropertyApplyResult
from now_workbench.releases import evaluate_release_prerequisites
from now_workbench.runbooks.engine import RunbookEngine
from now_workbench.runbooks.models import RunbookTestResult
from now_workbench.sdk.project import SdkProject, SdkProjectError, prepare_project
from now_workbench.sdk.runner import NowSdkRunner
from now_workbench.seed.engine import SeedEngine


class PipelineStepError(RuntimeError):
    """Raised when a pipeline step (such as the SDK deploy) fails."""


class DemoEvaluationResult(BaseModel):
    """Assessment of all requirements needed to run a demo bundle against an instance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_id: str
    instance_id: str
    instance_name: str
    sn_release: str
    min_release: str = "Xanadu"
    release_compatible: bool = True
    release_reason: str = ""
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
        path = safe_child(self.bundles_dir, bundle_id)
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

        rel_eval = evaluate_release_prerequisites(
            instance_release=instance.release,
            min_release=info.manifest.min_release,
            tags=info.manifest.tags,
        )

        is_ready = plugin_eval.all_satisfied and rel_eval.is_compatible

        return DemoEvaluationResult(
            bundle_id=bundle_id,
            instance_id=instance.id,
            instance_name=instance.name,
            sn_release=info.manifest.sn_release,
            min_release=info.manifest.min_release,
            release_compatible=rel_eval.is_compatible,
            release_reason=rel_eval.reason,
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
    ) -> PropertyApplyResult:
        """Apply the demo bundle system properties with snapshot backup."""
        bundle_path = self._get_bundle_path(bundle_id)
        return await self.prop_engine.apply_bundle_properties(
            bundle_id=bundle_id,
            bundle_path=bundle_path,
            instance=instance,
            fake_mode=fake_mode,
        )

    async def deploy_and_seed(
        self,
        bundle_id: str,
        instance: InstanceRecord,
        fake_mode: bool = False,
    ) -> tuple[SeedOperationRecord, str, dict[str, str]]:
        """Deploy the bundle's Fluent app and seed demo records (ADR-022).

        A bundle that is already an SDK project (package.json) is installed as is. A bundle
        with Fluent sources gets a generated project scoped to the instance's vendor prefix;
        its tables are renamed into that scope and the seed records follow the rename.

        Returns:
            The seed operation, what happened to the deploy step, and the table rename map.

        Raises:
            PipelineStepError: The app could not be generated, built or installed.
        """
        bundle_path = self._get_bundle_path(bundle_id)
        simulated = fake_mode or instance.url.startswith("fake://")
        table_map: dict[str, str] = {}

        if (bundle_path / "package.json").exists():
            await self._install(bundle_path, instance, fake_mode)
            deploy_note = "Fluent app deployed."
        elif not list((bundle_path / "fluent").glob("*.now.ts")):
            deploy_note = "Deploy skipped: the bundle has no Fluent sources."
        elif simulated:
            deploy_note = "Fluent app deploy simulated (fake instance)."
        else:
            project = await self._generate_project(bundle_id, bundle_path, instance)
            await self._install(project.path, instance, fake_mode)
            table_map = project.table_map
            deploy_note = (
                f"Fluent app deployed in scope {project.scope} "
                f"({len(table_map)} table(s) created in that scope)."
            )

        seed_engine = SeedEngine(repository=self.repo, fake_mode=fake_mode)
        seed = await seed_engine.load_and_seed(
            bundle_id=bundle_id,
            bundle_path=bundle_path,
            instance_id=instance.id,
            table_map=table_map,
        )
        return seed, deploy_note, table_map

    async def _generate_project(
        self, bundle_id: str, bundle_path: Path, instance: InstanceRecord
    ) -> SdkProject:
        vendor_key = "glide.appcreator.company.code"
        vendor = (await PropertyEngine().read_live_values([vendor_key], instance)).get(vendor_key)
        if not vendor:
            raise PipelineStepError(
                f"Could not read the vendor prefix ({vendor_key}) from {instance.name}."
            )
        name = self.bundle_manager.inspect_bundle(bundle_path).manifest.name
        try:
            return await prepare_project(
                bundle_path, bundle_id, name, vendor, settings.workspace_dir
            )
        except SdkProjectError as exc:
            raise PipelineStepError(f"Fluent app could not be built: {exc}") from exc

    async def _install(self, project_dir: Path, instance: InstanceRecord, fake_mode: bool) -> None:
        result = await NowSdkRunner(fake_mode=fake_mode).deploy(
            project_dir=project_dir,
            instance_url=instance.url,
            username=instance.username,
            password=instance.password,
        )
        if not result.success:
            raise PipelineStepError(
                f"SDK deploy failed (exit code {result.exit_code}): {result.output.strip()}"
            )

    async def test_demo_script(
        self,
        bundle_id: str,
        instance: InstanceRecord,
        fake_mode: bool = False,
        table_map: dict[str, str] | None = None,
    ) -> RunbookTestResult:
        """Test all walkthrough runbook stages against the instance.

        Args:
            bundle_id: Bundle id.
            instance: Target instance.
            fake_mode: Simulate the checks.
            table_map: Table renames from a deployed Fluent app (ADR-022).
        """
        bundle_path = self._get_bundle_path(bundle_id)
        guide = self.runbook_engine.load_runbook(bundle_path, bundle_id=bundle_id)
        if guide and table_map:
            guide = guide.model_copy(
                update={
                    "stages": [
                        st.model_copy(
                            update={
                                "target_table": table_map.get(
                                    st.target_table or "", st.target_table
                                )
                            }
                        )
                        for st in guide.stages
                    ]
                }
            )
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
            instance_id=instance.id,
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
            release=instance.release,
        )

    async def run_full_pipeline(
        self,
        bundle_id: str,
        instance: InstanceRecord,
        fake_mode: bool = False,
        record_video: bool = True,
    ) -> DemoPipelineSummary:
        """Execute the full end-to-end demo lifecycle and record video proof."""
        # 0. Evaluate platform release compatibility
        eval_res = self.evaluate_bundle(bundle_id, instance, fake_mode=fake_mode)
        if not eval_res.release_compatible:
            return DemoPipelineSummary(
                bundle_id=bundle_id,
                instance_name=instance.name,
                status="incompatible",
                message=f"Pipeline aborted: {eval_res.release_reason}",
                test_passed=False,
            )

        # 1. Evaluate & install modules
        installed_plugins = self.install_required_modules(bundle_id, instance, fake_mode=fake_mode)

        # 2. Configure properties
        prop_result = await self.configure_properties(bundle_id, instance, fake_mode=fake_mode)
        if not prop_result.success:
            return DemoPipelineSummary(
                bundle_id=bundle_id,
                instance_name=instance.name,
                installed_modules=[p.plugin_id for p in installed_plugins],
                applied_properties_count=prop_result.applied_count,
                status="failed",
                message="Pipeline aborted: property configuration failed: "
                + "; ".join(prop_result.details),
                test_passed=False,
            )

        # 3. Deploy & seed demo records
        try:
            seed_result, deploy_note, table_map = await self.deploy_and_seed(
                bundle_id, instance, fake_mode=fake_mode
            )
        except PipelineStepError as exc:
            return DemoPipelineSummary(
                bundle_id=bundle_id,
                instance_name=instance.name,
                installed_modules=[p.plugin_id for p in installed_plugins],
                applied_properties_count=prop_result.applied_count,
                status="failed",
                message=f"Pipeline aborted: {exc}",
                test_passed=False,
            )

        # 4. Test demo script runbook stages
        test_result = await self.test_demo_script(
            bundle_id, instance, fake_mode=fake_mode, table_map=table_map
        )

        # 5. Record video proof
        video_url = ""
        video_filename = ""
        video_note = "No video requested."
        if record_video:
            try:
                proof = await self.record_video_proof(
                    bundle_id=bundle_id,
                    instance=instance,
                    caption=f"Verified Demo Execution Proof - {bundle_id}",
                    fake_mode=fake_mode,
                )
            except CaptureFailedError as exc:
                video_note = f"Video proof not recorded: {exc}"
            else:
                video_url, video_filename = proof.url, proof.filename
                video_note = f"Video proof recorded: {video_filename}"

        still_missing = self.evaluate_bundle(bundle_id, instance, fake_mode=fake_mode)
        missing = still_missing.missing_plugins
        n_props = prop_result.applied_count
        n_rec = len(seed_result.created_records)
        stg_pass = test_result.passed_stages
        stg_tot = test_result.total_stages
        complete = test_result.all_passed and not missing and (video_url or not record_video)
        lead = "Demo pipeline completed" if complete else "Demo pipeline finished with problems"
        msg = (
            f"{lead} for '{bundle_id}' on {instance.name}: "
            f"{len(still_missing.required_plugins) - len(missing)}/"
            f"{len(still_missing.required_plugins)} required modules active"
            + (f", still missing: {', '.join(missing)}" if missing else "")
            + f"; {n_props} properties configured; {deploy_note} {n_rec} records seeded; "
            f"{stg_pass}/{stg_tot} stages verified. {video_note}"
        )

        return DemoPipelineSummary(
            bundle_id=bundle_id,
            instance_name=instance.name,
            installed_modules=[p.plugin_id for p in installed_plugins],
            applied_properties_count=n_props,
            seeded_records_count=n_rec,
            tested_stages_count=test_result.total_stages,
            test_passed=test_result.all_passed,
            video_proof_url=video_url,
            video_proof_filename=video_filename,
            status="success" if complete else "partial",
            message=msg,
        )
