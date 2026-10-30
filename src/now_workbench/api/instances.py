"""API routes for managing ServiceNow instances in the registry."""

from typing import Any

from fastapi import APIRouter, HTTPException

from now_workbench.connectivity import verify_instance_authentication
from now_workbench.db import (
    InstanceCreate,
    InstanceRecord,
    InstanceUpdate,
    db_session,
)

router = APIRouter(prefix="/api/instances", tags=["instances"])


@router.get("", response_model=list[InstanceRecord])
def list_instances() -> list[InstanceRecord]:
    """List all registered ServiceNow instances."""
    with db_session() as repo:
        return repo.list_instances()


@router.post("", response_model=InstanceRecord)
def register_instance(inst: InstanceCreate) -> InstanceRecord:
    """Register a new instance and verify initial status."""
    with db_session() as repo:
        created = repo.add_instance(inst)
        prefs = repo.get_workbench_preferences()
        status, _, _ = verify_instance_authentication(created, fake_mode=prefs.sdk_fake_mode)
        repo.update_instance_status(created.id, status)
        return repo.get_instance(created.id) or created


@router.put("/{instance_id}", response_model=InstanceRecord)
def update_instance_endpoint(instance_id: str, update: InstanceUpdate) -> InstanceRecord:
    """Update an existing instance (rename, credentials, release) and auto-verify."""
    with db_session() as repo:
        rec = repo.update_instance(instance_id, update)
        if not rec:
            raise HTTPException(status_code=404, detail="Instance not found.")
        prefs = repo.get_workbench_preferences()
        status, _, _ = verify_instance_authentication(rec, fake_mode=prefs.sdk_fake_mode)
        repo.update_instance_status(instance_id, status)
        return repo.get_instance(instance_id) or rec


@router.delete("/{instance_id}")
def delete_instance_endpoint(instance_id: str) -> dict[str, Any]:
    """Delete an instance from the registry."""
    with db_session() as repo:
        ok = repo.delete_instance(instance_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Instance not found.")
    return {"success": True, "deleted_instance_id": instance_id}


@router.post("/test-all")
def test_all_instances(fake_mode: bool = False) -> dict[str, Any]:
    """Test connectivity and authentication across all registered instances."""
    with db_session() as repo:
        instances = repo.list_instances()
        prefs = repo.get_workbench_preferences()
        is_simulated = fake_mode or prefs.sdk_fake_mode
        results: list[dict[str, Any]] = []
        auth_count = 0
        for inst in instances:
            status, msg, code = verify_instance_authentication(
                inst, timeout=3.5, fake_mode=is_simulated
            )
            repo.update_instance_status(inst.id, status)
            if status == "authenticated":
                auth_count += 1
            results.append(
                {
                    "id": inst.id,
                    "name": inst.name,
                    "status": status,
                    "message": msg,
                    "http_code": code,
                }
            )
        fail_count = len(instances) - auth_count
        return {
            "total": len(instances),
            "authenticated": auth_count,
            "unauthenticated": fail_count,
            "results": results,
        }


@router.post("/cleanup")
def cleanup_unauthenticated_instances() -> dict[str, Any]:
    """Delete all instances whose status is not 'authenticated'."""
    with db_session() as repo:
        instances = repo.list_instances()
        deleted_ids: list[str] = []
        deleted_names: list[str] = []
        for inst in instances:
            if inst.status != "authenticated":
                if repo.delete_instance(inst.id):
                    deleted_ids.append(inst.id)
                    deleted_names.append(inst.name)
        remaining = repo.list_instances()
        if remaining and not any(r.is_default for r in remaining):
            repo.set_default_instance(remaining[0].id)
            remaining = repo.list_instances()
        return {
            "deleted_count": len(deleted_ids),
            "deleted_ids": deleted_ids,
            "deleted_names": deleted_names,
            "remaining_count": len(remaining),
        }


@router.post("/{instance_id}/activate")
def activate_instance(instance_id: str) -> dict[str, Any]:
    """Set the specified instance as active default."""
    with db_session() as repo:
        ok = repo.set_default_instance(instance_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Instance not found.")
    return {"success": True, "active_instance_id": instance_id}


@router.post("/{instance_id}/test")
def test_instance(instance_id: str, fake_mode: bool = False) -> dict[str, Any]:
    """Test connectivity and authentication for a registered instance."""
    with db_session() as repo:
        inst = repo.get_instance(instance_id)
        if not inst:
            raise HTTPException(status_code=404, detail="Instance not found.")

        prefs = repo.get_workbench_preferences()
        is_simulated = fake_mode or prefs.sdk_fake_mode
        status, msg, code = verify_instance_authentication(inst, fake_mode=is_simulated)
        repo.update_instance_status(instance_id, status)
        return {
            "success": status == "authenticated",
            "status": status,
            "message": msg,
            "http_code": code,
            "username": inst.username,
        }
