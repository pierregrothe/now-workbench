# src/now_workbench/interfaces/api/properties.py
# System properties of a demo: inspect, apply with a snapshot, restore.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Demo property endpoints (snapshot before apply, restore after)."""

from typing import Any

from fastapi import APIRouter

from now_workbench.domains.instances import InstanceRepository
from now_workbench.domains.properties import PropertyEngine
from now_workbench.interfaces.api.demo_support import (
    PropertyActionRequest,
    require_bundle,
    target_instance,
)
from now_workbench.platform.db.session import db_session

__all__ = [
    "router",
    "apply_bundle_properties",
    "get_bundle_properties",
    "restore_bundle_properties",
]

router = APIRouter(prefix="/api/demos", tags=["properties"])


@router.get("/{bundle_id}/properties")
def get_bundle_properties(bundle_id: str, instance_id: str | None = None) -> dict[str, Any]:
    """Retrieve configured properties and active snapshot status for a demo."""
    target = require_bundle(bundle_id).path
    prop_engine = PropertyEngine()
    props = prop_engine.read_bundle_properties(target)

    with db_session() as conn:
        inst = InstanceRepository(conn).resolve(instance_id)
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
    target = require_bundle(bundle_id).path

    with db_session() as conn:
        inst = target_instance(conn, req.instance_id)

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
    require_bundle(bundle_id)

    with db_session() as conn:
        inst = target_instance(conn, req.instance_id)

    prop_engine = PropertyEngine()
    res = await prop_engine.restore_properties(
        bundle_id=bundle_id,
        instance=inst,
        fake_mode=req.fake_mode,
    )
    return res.model_dump()
