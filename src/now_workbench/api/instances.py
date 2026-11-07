"""API routes for the signed-in person's own ServiceNow instances (ADR-018)."""

from typing import Any

from fastapi import APIRouter, HTTPException

from now_workbench.connectivity import check_and_record_instance
from now_workbench.db import (
    InstanceCreate,
    InstancePublic,
    InstanceUpdate,
    db_session,
)
from now_workbench.db.repos.instances import InstanceRepository
from now_workbench.db.repos.preferences import PreferencesRepository

router = APIRouter(prefix="/api/instances", tags=["instances"])


@router.get("", response_model=list[InstancePublic])
def list_instances() -> list[InstancePublic]:
    """List registered instances with their detected platform profile (passwords withheld)."""
    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        return [
            inst.to_public(instance_repo.get_instance_profile(inst.id))
            for inst in instance_repo.list_instances()
        ]


@router.post("", response_model=InstancePublic)
def register_instance(inst: InstanceCreate) -> InstancePublic:
    """Register a new instance and verify initial status."""
    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        try:
            created = instance_repo.add_instance(inst)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        prefs = PreferencesRepository(conn).get_workbench_preferences()
        check_and_record_instance(conn, created, fake_mode=prefs.sdk_fake_mode)
        return (instance_repo.get_instance(created.id) or created).to_public(
            instance_repo.get_instance_profile(created.id)
        )


@router.put("/{instance_id}", response_model=InstancePublic)
def update_instance_endpoint(instance_id: str, update: InstanceUpdate) -> InstancePublic:
    """Update an existing instance (rename, credentials, release) and auto-verify."""
    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        try:
            rec = instance_repo.update_instance(instance_id, update)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if not rec:
            raise HTTPException(status_code=404, detail="Instance not found.")
        prefs = PreferencesRepository(conn).get_workbench_preferences()
        check_and_record_instance(conn, rec, fake_mode=prefs.sdk_fake_mode)
        return (instance_repo.get_instance(instance_id) or rec).to_public(
            instance_repo.get_instance_profile(rec.id)
        )


@router.delete("/{instance_id}")
def delete_instance_endpoint(instance_id: str) -> dict[str, Any]:
    """Delete an instance from the registry."""
    with db_session() as conn:
        ok = InstanceRepository(conn).delete_instance(instance_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Instance not found.")
    return {"success": True, "deleted_instance_id": instance_id}


@router.post("/test-all")
def test_all_instances(fake_mode: bool = False) -> dict[str, Any]:
    """Test connectivity and authentication across all registered instances."""
    with db_session() as conn:
        instances = InstanceRepository(conn).list_instances()
        prefs = PreferencesRepository(conn).get_workbench_preferences()
        is_simulated = fake_mode or prefs.sdk_fake_mode
        results: list[dict[str, Any]] = []
        auth_count = 0
        for inst in instances:
            status, msg, code = check_and_record_instance(
                conn, inst, timeout=3.5, fake_mode=is_simulated
            )
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
    with db_session() as conn:
        instance_repo = InstanceRepository(conn)
        instances = instance_repo.list_instances()
        deleted_ids: list[str] = []
        deleted_names: list[str] = []
        for inst in instances:
            if inst.status != "authenticated":
                if instance_repo.delete_instance(inst.id):
                    deleted_ids.append(inst.id)
                    deleted_names.append(inst.name)
        # delete_instance re-elects a default itself, so nothing to repair here.
        remaining = instance_repo.list_instances()
        return {
            "deleted_count": len(deleted_ids),
            "deleted_ids": deleted_ids,
            "deleted_names": deleted_names,
            "remaining_count": len(remaining),
        }


@router.post("/{instance_id}/activate")
def activate_instance(instance_id: str) -> dict[str, Any]:
    """Set the specified instance as active default."""
    with db_session() as conn:
        ok = InstanceRepository(conn).set_default_instance(instance_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Instance not found.")
    return {"success": True, "active_instance_id": instance_id}


@router.post("/{instance_id}/test")
def test_instance(instance_id: str, fake_mode: bool = False) -> dict[str, Any]:
    """Test connectivity and authentication for a registered instance."""
    with db_session() as conn:
        inst = InstanceRepository(conn).get_instance(instance_id)
        if not inst:
            raise HTTPException(status_code=404, detail="Instance not found.")

        prefs = PreferencesRepository(conn).get_workbench_preferences()
        is_simulated = fake_mode or prefs.sdk_fake_mode
        status, msg, code = check_and_record_instance(conn, inst, fake_mode=is_simulated)
        return {
            "success": status == "authenticated",
            "status": status,
            "message": msg,
            "http_code": code,
            "username": inst.username,
        }
