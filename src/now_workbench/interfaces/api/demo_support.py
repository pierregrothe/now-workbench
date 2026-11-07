# src/now_workbench/interfaces/api/demo_support.py
# Shared by the demo routers: bundle access checks, bundle info and the target instance.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Helpers shared by the demos, captures and properties routers."""

import sqlite3

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from now_workbench.domains.bundles import BundleManager, DemoBundleInfo
from now_workbench.domains.instances import InstanceRecord, InstanceRepository
from now_workbench.domains.sharing import (
    BundleAccess,
    ReadOnlyBundleError,
    resolve_bundle,
)
from now_workbench.platform.db.session import db_session

__all__ = ["PropertyActionRequest", "bundle_info", "require_bundle", "target_instance"]


class PropertyActionRequest(BaseModel):
    """Payload for property apply/restore and demo reset operations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    instance_id: str | None = Field(default=None, description="Optional target instance ID")
    fake_mode: bool = Field(default=False, description="Simulate operation without live HTTP")


def require_bundle(bundle_id: str, write: bool = False) -> BundleAccess:
    """Resolve a bundle for the signed-in person (ADR-018): 404 unless theirs or shared."""
    with db_session() as conn:
        try:
            return resolve_bundle(conn, bundle_id, write=write)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail="Demo bundle not found.") from exc
        except ReadOnlyBundleError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc


def bundle_info(access: BundleAccess) -> DemoBundleInfo:
    info = BundleManager(storage_dir=access.root).inspect_bundle(access.path)
    return info.model_copy(
        update={"owner_email": access.owner, "access": access.kind.value, "version": access.version}
    )


def target_instance(
    conn: sqlite3.Connection, instance_id: str | None, missing: str = "Target instance not found."
) -> InstanceRecord:
    """Return the requested (or default) instance; HTTP 400 with ``missing`` when there is none."""
    inst = InstanceRepository(conn).resolve(instance_id)
    if inst is None:
        raise HTTPException(status_code=400, detail=missing)
    return inst
