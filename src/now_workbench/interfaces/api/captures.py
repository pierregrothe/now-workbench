# src/now_workbench/interfaces/api/captures.py
# Screenshots and videos of a demo: list, take, download, rename and delete.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Demo capture endpoints (ADR-013 follow-up: real captures only)."""

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

from now_workbench.domains.capture import (
    CaptureArtifact,
    CaptureFailedError,
    CaptureRequest,
    PlaywrightCaptureEngine,
)
from now_workbench.domains.instances import InstanceRepository, is_simulated
from now_workbench.domains.settings import PreferencesRepository
from now_workbench.interfaces.api.demo_support import require_bundle
from now_workbench.platform.config.paths import safe_child
from now_workbench.platform.config.settings import settings
from now_workbench.platform.db.session import db_session

__all__ = [
    "CaptureUpdateRequest",
    "router",
    "clear_demo_captures",
    "create_demo_capture",
    "delete_demo_capture_file",
    "get_demo_capture_file",
    "list_demo_captures",
    "update_demo_capture_file",
]

router = APIRouter(prefix="/api/demos", tags=["captures"])


class CaptureUpdateRequest(BaseModel):
    """Payload to update capture artifact metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str


@router.get("/{bundle_id}/captures", response_model=list[CaptureArtifact])
def list_demo_captures(bundle_id: str) -> list[CaptureArtifact]:
    """List all Playwright screenshots and videos captured for a demo bundle."""
    engine = PlaywrightCaptureEngine(bundles_dir=require_bundle(bundle_id).root)
    return engine.list_captures(bundle_id)


@router.post("/{bundle_id}/captures", response_model=CaptureArtifact)
async def create_demo_capture(bundle_id: str, req: CaptureRequest) -> CaptureArtifact:
    """Capture a screenshot or video of the target instance for this bundle (owner only)."""
    require_bundle(bundle_id, write=True)
    with db_session() as conn:
        prefs = PreferencesRepository(conn).get_workbench_preferences()
        inst = InstanceRepository(conn).resolve(req.instance_id)
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
        fake_mode=is_simulated(inst, req.fake_mode or prefs.capture_fake_mode),
    )
    try:
        return await engine.capture(
            merged_req,
            instance_url=inst_url,
            wait_timeout_ms=prefs.capture_wait_timeout_ms,
            username=username,
            password=password,
            release=inst.release,
        )
    except CaptureFailedError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{bundle_id}/captures/{filename}")
def get_demo_capture_file(bundle_id: str, filename: str) -> FileResponse:
    """Serve a captured screenshot (.png) or video (.webm) file inline for browser viewing."""
    file_path = safe_child(require_bundle(bundle_id).path / "media", filename)
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
    require_bundle(bundle_id, write=True)
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
    require_bundle(bundle_id, write=True)
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
    require_bundle(bundle_id, write=True)
    engine = PlaywrightCaptureEngine(bundles_dir=settings.get_bundles_dir())
    try:
        return engine.update_capture(bundle_id, filename, label=req.label)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
