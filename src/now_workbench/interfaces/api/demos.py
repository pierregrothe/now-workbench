"""API routes for demonstration bundles and transactional seed operations."""

import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.background import BackgroundTask

from now_workbench.domains.bundles import BundleManager, DemoBundleInfo
from now_workbench.domains.capture import (
    CaptureArtifact,
    CaptureFailedError,
    CaptureRequest,
    PlaywrightCaptureEngine,
)
from now_workbench.domains.demos import (
    DemoEvaluationResult,
    DemoPipelineEngine,
    DemoPipelineSummary,
)
from now_workbench.domains.fluent import FluentEngine
from now_workbench.domains.instances import InstanceRepository
from now_workbench.domains.properties import PropertyEngine
from now_workbench.domains.runbooks import RunbookEngine, RunbookGuide
from now_workbench.domains.seed import SeedEngine, SeedOperationRecord, SeedRepository
from now_workbench.domains.settings import PreferencesRepository
from now_workbench.domains.sharing import (
    ArtifactRepository,
    BundleAccess,
    ReadOnlyBundleError,
    delete_artifact_files,
    list_accessible,
    register_new_bundle,
    resolve_bundle,
)
from now_workbench.domains.synthesizer import (
    NoReleaseError,
    SynthesizedDemoResult,
    UseCaseSynthesisRequest,
    UseCaseSynthesizer,
    resolve_synthesis_release,
)
from now_workbench.platform.config.paths import safe_child
from now_workbench.platform.config.settings import settings
from now_workbench.platform.db.session import db_session
from now_workbench.platform.owner import current_owner

router = APIRouter(prefix="/api/demos", tags=["demos"])


class StageVerificationRequest(BaseModel):
    """Payload for stage state verification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    step_number: int = Field(..., description="1-based sequence index")
    instance_id: str | None = Field(default=None, description="Optional target instance ID")
    fake_mode: bool = Field(default=False, description="Simulate Table API verification")


class DemoBundleUpdateRequest(BaseModel):
    """Payload to update demo bundle metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None


class CaptureUpdateRequest(BaseModel):
    """Payload to update capture artifact metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str


class PropertyActionRequest(BaseModel):
    """Payload for property apply/restore and demo reset operations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    instance_id: str | None = Field(default=None, description="Optional target instance ID")
    fake_mode: bool = Field(default=False, description="Simulate operation without live HTTP")


class FluentDiffRequest(BaseModel):
    """Payload for comparing two demo bundle Fluent schemas."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_bundle_id: str = Field(..., description="Target bundle to compare against")


class CloneBundleRequest(BaseModel):
    """Payload for cloning a demo bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_bundle_id: str = Field(..., description="Unique slug for the new cloned bundle")
    target_name: str | None = Field(
        default=None, description="Optional human-readable display name"
    )


def _access(bundle_id: str, write: bool = False) -> BundleAccess:
    """Resolve a bundle for the signed-in person (ADR-018): 404 unless theirs or shared."""
    with db_session() as conn:
        try:
            return resolve_bundle(conn, bundle_id, write=write)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail="Demo bundle not found.") from exc
        except ReadOnlyBundleError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc


def _info(access: BundleAccess) -> DemoBundleInfo:
    info = BundleManager(storage_dir=access.root).inspect_bundle(access.path)
    return info.model_copy(
        update={"owner_email": access.owner, "access": access.kind.value, "version": access.version}
    )


@router.get("", response_model=list[DemoBundleInfo])
def list_demos() -> list[DemoBundleInfo]:
    """List the signed-in person's demo bundles and those shared with them."""
    with db_session() as conn:
        accesses = list_accessible(conn)
    infos = [_info(a) for a in accesses]
    return sorted(infos, key=lambda b: b.manifest.name)


@router.get("/{bundle_id}", response_model=DemoBundleInfo)
def get_demo_detail(bundle_id: str) -> DemoBundleInfo:
    """Inspect metadata for a demonstration package."""
    return _info(_access(bundle_id))


@router.post("/{bundle_id}/clone", response_model=DemoBundleInfo)
def clone_demo_bundle(bundle_id: str, req: CloneBundleRequest) -> DemoBundleInfo:
    """Clone a bundle (own or shared) into a new bundle the signed-in person owns."""
    source = _access(bundle_id)
    mgr = BundleManager(storage_dir=settings.get_bundles_dir())
    try:
        info = mgr.clone_bundle(
            source_id=bundle_id,
            target_id=req.target_bundle_id,
            target_name=req.target_name,
            source_root=source.root,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (FileExistsError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    with db_session() as conn:
        register_new_bundle(conn, info.manifest.id, current_owner())
    return _info(_access(info.manifest.id))


@router.delete("/{bundle_id}")
def delete_demo(bundle_id: str) -> dict[str, Any]:
    """Delete a demonstration bundle, its versions and its shares (owner only)."""
    _access(bundle_id, write=True)
    mgr = BundleManager(storage_dir=settings.get_bundles_dir())
    try:
        mgr.delete_bundle(bundle_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    with db_session() as conn:
        ArtifactRepository(conn).forget_artifact(bundle_id)
    delete_artifact_files(bundle_id)
    return {
        "success": True,
        "bundle_id": bundle_id,
        "message": f"Demonstration bundle '{bundle_id}' deleted successfully.",
    }


@router.patch("/{bundle_id}", response_model=DemoBundleInfo)
def update_demo_bundle(bundle_id: str, req: DemoBundleUpdateRequest) -> DemoBundleInfo:
    """Update a demonstration bundle's manifest metadata (owner only)."""
    _access(bundle_id, write=True)
    mgr = BundleManager(storage_dir=settings.get_bundles_dir())
    try:
        mgr.update_bundle_manifest(
            bundle_id=bundle_id,
            name=req.name,
            description=req.description,
            tags=req.tags,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _info(_access(bundle_id))


@router.get("/{bundle_id}/export")
def export_demo(bundle_id: str) -> FileResponse:
    """Export a demonstration package as a portable .sn-demo.zip archive.

    The archive is built in a private temporary file and deleted once it has been sent, so
    exports never pile up on the server.
    """
    access = _access(bundle_id)
    mgr = BundleManager(storage_dir=access.root)
    fd, tmp_name = tempfile.mkstemp(suffix=".sn-demo.zip")
    os.close(fd)
    output_file = Path(tmp_name)
    try:
        mgr.export_bundle(bundle_id, output_file)
    except Exception as e:
        output_file.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))
    return FileResponse(
        path=output_file,
        filename=f"{bundle_id}.sn-demo.zip",
        media_type="application/zip",
        background=BackgroundTask(output_file.unlink, missing_ok=True),
    )


@router.post("/{bundle_id}/seed", response_model=SeedOperationRecord)
async def seed_demo_records(
    bundle_id: str,
    payload: dict[str, Any] | None = None,
) -> SeedOperationRecord:
    """Transactionally load and seed records into ServiceNow Table API."""
    bundle_path = _access(bundle_id).path

    body = payload or {}
    instance_id = body.get("instance_id")
    fake_mode = bool(body.get("fake_mode", False))

    with db_session() as conn:
        engine = SeedEngine(conn=conn, fake_mode=fake_mode)
        try:
            return await engine.load_and_seed(bundle_id, bundle_path, instance_id=instance_id)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@router.post("/seed/{operation_id}/rollback")
async def rollback_seed_records(
    operation_id: str,
    fake_mode: bool = False,
) -> dict[str, Any]:
    """Roll back (delete) all records created in a previous seed operation."""
    with db_session() as conn:
        engine = SeedEngine(conn=conn, fake_mode=fake_mode)
        try:
            deleted_count, errors = await engine.rollback(operation_id)
            return {
                "success": len(errors) == 0,
                "operation_id": operation_id,
                "deleted_count": deleted_count,
                "errors": errors,
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@router.get("/seed/operations", response_model=list[SeedOperationRecord])
def list_seed_history(limit: int = 50) -> list[SeedOperationRecord]:
    """Retrieve audit history of demo seed runs."""
    with db_session() as conn:
        return SeedRepository(conn).list_seed_operations(limit=limit)


@router.get("/{bundle_id}/runbook", response_model=RunbookGuide)
def get_demo_runbook(bundle_id: str) -> RunbookGuide:
    """Retrieve structured walkthrough guide and persona stages for a demonstration."""
    engine = RunbookEngine()
    target = _access(bundle_id).path
    runbook = engine.load_runbook(target, bundle_id=bundle_id)
    if not runbook:
        raise HTTPException(status_code=404, detail="Demonstration walkthrough guide not found.")
    return runbook


@router.post("/{bundle_id}/runbook/verify-stage")
async def verify_demo_stage(
    bundle_id: str,
    req: StageVerificationRequest,
) -> dict[str, Any]:
    """Verify live ServiceNow instance state for a demonstration stage."""
    engine = RunbookEngine()
    target = _access(bundle_id).path
    runbook = engine.load_runbook(target, bundle_id=bundle_id)
    if not runbook:
        raise HTTPException(status_code=404, detail="Demonstration walkthrough guide not found.")

    matching_stage = next((s for s in runbook.stages if s.step_number == req.step_number), None)
    if not matching_stage:
        raise HTTPException(
            status_code=404, detail=f"Stage {req.step_number} not found in runbook."
        )

    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        inst = (
            instance_repo.get_instance(req.instance_id)
            if req.instance_id
            else instance_repo.get_default_instance()
        )
    if not inst:
        raise HTTPException(status_code=400, detail="Target instance not found.")

    ok, msg = await engine.verify_stage(matching_stage, inst, fake_mode=req.fake_mode)
    return {
        "success": ok,
        "step_number": req.step_number,
        "bundle_id": bundle_id,
        "instance_id": inst.id,
        "message": msg,
    }


@router.get("/{bundle_id}/properties")
def get_bundle_properties(bundle_id: str, instance_id: str | None = None) -> dict[str, Any]:
    """Retrieve configured properties and active snapshot status for a demo."""
    target = _access(bundle_id).path
    prop_engine = PropertyEngine()
    props = prop_engine.read_bundle_properties(target)

    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        inst = (
            instance_repo.get_instance(instance_id)
            if instance_id
            else instance_repo.get_default_instance()
        )
    snapshot = prop_engine.load_snapshot(bundle_id, inst.id) if inst else None

    return {
        "bundle_id": bundle_id,
        "instance_id": inst.id if inst else None,
        "properties": props,
        "has_snapshot": snapshot is not None,
        "snapshot": snapshot.model_dump() if snapshot else None,
    }


@router.post("/{bundle_id}/properties/apply")
async def apply_bundle_properties(
    bundle_id: str,
    req: PropertyActionRequest,
) -> dict[str, Any]:
    """Apply bundle properties to target instance and record snapshot."""
    target = _access(bundle_id).path

    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        inst = (
            instance_repo.get_instance(req.instance_id)
            if req.instance_id
            else instance_repo.get_default_instance()
        )
    if not inst:
        raise HTTPException(status_code=400, detail="Target instance not found.")

    prop_engine = PropertyEngine()
    res = await prop_engine.apply_bundle_properties(
        bundle_id=bundle_id,
        bundle_path=target,
        instance=inst,
        fake_mode=req.fake_mode,
    )
    return res.model_dump()


@router.post("/{bundle_id}/properties/restore")
async def restore_bundle_properties(
    bundle_id: str,
    req: PropertyActionRequest,
) -> dict[str, Any]:
    """Restore previous property states from snapshot for target instance."""
    _access(bundle_id)

    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        inst = (
            instance_repo.get_instance(req.instance_id)
            if req.instance_id
            else instance_repo.get_default_instance()
        )
    if not inst:
        raise HTTPException(status_code=400, detail="Target instance not found.")

    prop_engine = PropertyEngine()
    res = await prop_engine.restore_properties(
        bundle_id=bundle_id,
        instance=inst,
        fake_mode=req.fake_mode,
    )
    return res.model_dump()


@router.post("/{bundle_id}/reset")
async def reset_demo(
    bundle_id: str,
    req: PropertyActionRequest,
) -> dict[str, Any]:
    """Unified teardown: roll back seed data records and restore system properties."""
    _access(bundle_id)

    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        inst = (
            instance_repo.get_instance(req.instance_id)
            if req.instance_id
            else instance_repo.get_default_instance()
        )
        if not inst:
            raise HTTPException(status_code=400, detail="Target instance not found.")

        # 1. Roll back active seed records for this bundle and instance
        seed_engine = SeedEngine(conn=conn, fake_mode=req.fake_mode)
        active_ops = [
            op
            for op in SeedRepository(conn).list_seed_operations(limit=100)
            if op.bundle_id == bundle_id
            and op.status != "rolled_back"
            and op.instance_id == inst.id
        ]
        seed_rolled_back = 0
        seed_errors: list[str] = []
        for op in active_ops:
            count, op_errors = await seed_engine.rollback(op.id)
            seed_rolled_back += count
            seed_errors.extend(op_errors)

    # 2. Restore properties
    prop_engine = PropertyEngine()
    prop_res = await prop_engine.restore_properties(
        bundle_id=bundle_id,
        instance=inst,
        fake_mode=req.fake_mode,
    )

    return {
        "success": prop_res.success and not seed_errors,
        "bundle_id": bundle_id,
        "instance_id": inst.id,
        "seed_records_rolled_back": seed_rolled_back,
        "properties_restored": prop_res.restored_count,
        "details": prop_res.details,
        "errors": seed_errors,
    }


@router.get("/{bundle_id}/fluent")
def get_demo_fluent_schema(bundle_id: str) -> dict[str, Any]:
    """Retrieve parsed ServiceNow Fluent SDK table schemas for a demo bundle."""
    target = _access(bundle_id).path

    engine = FluentEngine()
    tables = engine.load_bundle_schemas(target)
    return {
        "bundle_id": bundle_id,
        "tables": [t.model_dump() for t in tables],
    }


@router.post("/{bundle_id}/fluent/diff")
def diff_demo_fluent_schema(
    bundle_id: str,
    req: FluentDiffRequest,
) -> dict[str, Any]:
    """Compute structural Fluent schema diff between source bundle and target bundle."""
    source_target = _access(bundle_id).path
    compare_target = _access(req.target_bundle_id).path

    engine = FluentEngine()
    schemas_a = engine.load_bundle_schemas(source_target)
    schemas_b = engine.load_bundle_schemas(compare_target)
    diff = engine.compute_diff(schemas_a, schemas_b)

    return diff.model_dump()


@router.post("/synthesize", response_model=SynthesizedDemoResult)
def synthesize_demo_bundle(req: UseCaseSynthesisRequest) -> SynthesizedDemoResult:
    """Synthesize a tailored demo bundle from a use case and customer context."""
    with db_session() as conn:
        prefs = PreferencesRepository(conn).get_workbench_preferences()
        try:
            release = resolve_synthesis_release(conn, req.sn_release, req.instance_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except NoReleaseError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    synthesizer = UseCaseSynthesizer(bundles_dir=settings.get_bundles_dir())
    result = synthesizer.synthesize(
        req.model_copy(update={"sn_release": release}),
        author_name=prefs.sc_author_name,
        scoped_prefix=prefs.default_scoped_prefix,
    )
    with db_session() as conn:
        register_new_bundle(conn, result.bundle_id, current_owner())
    return result


@router.get("/{bundle_id}/captures", response_model=list[CaptureArtifact])
def list_demo_captures(bundle_id: str) -> list[CaptureArtifact]:
    """List all Playwright screenshots and videos captured for a demo bundle."""
    engine = PlaywrightCaptureEngine(bundles_dir=_access(bundle_id).root)
    return engine.list_captures(bundle_id)


@router.post("/{bundle_id}/captures", response_model=CaptureArtifact)
async def create_demo_capture(bundle_id: str, req: CaptureRequest) -> CaptureArtifact:
    """Capture a screenshot or video of the target instance for this bundle (owner only)."""
    _access(bundle_id, write=True)
    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        prefs = PreferencesRepository(conn).get_workbench_preferences()
        inst = (
            instance_repo.get_instance(req.instance_id)
            if req.instance_id
            else instance_repo.get_default_instance()
        )
    if inst is None:
        if req.instance_id:
            raise HTTPException(status_code=404, detail="Instance not found.")
        raise HTTPException(status_code=409, detail="No target instance registered.")
    inst_url = inst.url
    username = inst.username
    password = inst.password
    engine = PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir())
    merged_req = CaptureRequest(
        bundle_id=bundle_id,
        instance_id=req.instance_id,
        target_path=req.target_path,
        media_type=req.media_type,
        label=req.label,
        viewport_width=req.viewport_width,
        viewport_height=req.viewport_height,
        fake_mode=req.fake_mode or prefs.capture_fake_mode,
    )
    try:
        return await engine.capture(
            merged_req,
            instance_url=inst_url,
            wait_timeout_ms=prefs.capture_wait_timeout_ms,
            username=username,
            password=password,
            release=inst.release if inst else "Xanadu",
        )
    except CaptureFailedError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{bundle_id}/captures/{filename}")
def get_demo_capture_file(bundle_id: str, filename: str) -> FileResponse:
    """Serve a captured screenshot (.png) or video (.webm) file inline for browser viewing."""
    file_path = safe_child(_access(bundle_id).path / "media", filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Capture file not found.")
    media_type = "video/webm" if filename.endswith(".webm") else "image/png"
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type,
        content_disposition_type="inline",
    )


@router.delete("/{bundle_id}/captures")
def clear_demo_captures(bundle_id: str) -> dict[str, Any]:
    """Delete all captured screenshots and videos associated with a demonstration bundle."""
    _access(bundle_id, write=True)
    engine = PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir())
    try:
        count = engine.clear_all_captures(bundle_id)
        return {
            "success": True,
            "bundle_id": bundle_id,
            "deleted_count": count,
            "message": f"Cleared {count} capture artifact(s) from bundle '{bundle_id}'.",
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{bundle_id}/captures/{filename}")
def delete_demo_capture_file(bundle_id: str, filename: str) -> dict[str, Any]:
    """Delete a captured screenshot (.png) or video (.webm) artifact."""
    _access(bundle_id, write=True)
    engine = PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir())
    try:
        engine.delete_capture(bundle_id, filename)
        return {
            "success": True,
            "bundle_id": bundle_id,
            "filename": filename,
            "message": f"Capture artifact '{filename}' deleted.",
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{bundle_id}/captures/{filename}", response_model=CaptureArtifact)
def update_demo_capture_file(
    bundle_id: str, filename: str, req: CaptureUpdateRequest
) -> CaptureArtifact:
    """Update label/caption of a screenshot (.png) or video (.webm) artifact."""
    _access(bundle_id, write=True)
    engine = PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir())
    try:
        return engine.update_capture(bundle_id, filename, label=req.label)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{bundle_id}/evaluate", response_model=DemoEvaluationResult)
def evaluate_demo_prerequisites(
    bundle_id: str,
    instance_id: str | None = None,
) -> DemoEvaluationResult:
    """Evaluate demo bundle prerequisites against the target or default instance."""
    bundles_dir = _access(bundle_id).root
    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        inst = (
            instance_repo.get_instance(instance_id)
            if instance_id
            else instance_repo.get_default_instance()
        )
        if not inst:
            raise HTTPException(status_code=400, detail="No active instance configured.")
        prefs = PreferencesRepository(conn).get_workbench_preferences()
        engine = DemoPipelineEngine(bundles_dir=bundles_dir, conn=conn)
        try:
            return engine.evaluate_bundle(bundle_id, inst, fake_mode=prefs.sdk_fake_mode)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))


@router.post("/{bundle_id}/pipeline", response_model=DemoPipelineSummary)
async def run_demo_pipeline_endpoint(
    bundle_id: str,
    instance_id: str | None = None,
    no_video: bool = False,
) -> DemoPipelineSummary:
    """Execute complete end-to-end demo lifecycle: evaluate, install modules,
    configure, seed, test, and record video proof. Owner only: it records media into the bundle.
    """
    _access(bundle_id, write=True)
    bundles_dir = settings.get_bundles_dir()
    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        inst = (
            instance_repo.get_instance(instance_id)
            if instance_id
            else instance_repo.get_default_instance()
        )
        if not inst:
            raise HTTPException(status_code=400, detail="No active instance configured.")
        prefs = PreferencesRepository(conn).get_workbench_preferences()
        engine = DemoPipelineEngine(bundles_dir=bundles_dir, conn=conn)
        try:
            return await engine.run_full_pipeline(
                bundle_id=bundle_id,
                instance=inst,
                fake_mode=prefs.sdk_fake_mode,
                record_video=not no_video,
            )
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
