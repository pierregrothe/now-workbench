"""System property inspection, transactional snapshotting, and restoration engine."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from now_workbench.config.settings import settings
from now_workbench.db.models import InstanceRecord
from now_workbench.properties.models import (
    PropertyApplyResult,
    PropertySnapshot,
)


def _load_bundle_properties(bundle_path: Path) -> dict[str, str]:
    """Load sys_properties.json dictionary from a bundle path."""
    for cand in [
        bundle_path / "properties" / "sys_properties.json",
        bundle_path / "sys_properties.json",
    ]:
        if cand.is_file():
            try:
                data = json.loads(cand.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return {str(k): str(v) for k, v in data.items()}
            except Exception:
                return {}
    return {}


def _get_snapshot_path(storage_dir: Path, bundle_id: str, instance_id: str) -> Path:
    """Return filesystem path for property snapshot record."""
    safe_bundle = bundle_id.replace("/", "_")
    safe_instance = instance_id.replace("/", "_")
    return storage_dir / f"{safe_bundle}_{safe_instance}.json"


def _build_auth(instance: InstanceRecord) -> Any:
    """Build httpx authentication for target instance."""
    if instance.auth_type == "basic":
        return httpx.BasicAuth(instance.username, instance.password)
    return None


class PropertyEngine:
    """Manages transactional application and rollback of ServiceNow system properties."""

    def __init__(self, snapshots_dir: Path | None = None) -> None:
        self.snapshots_dir = snapshots_dir or (settings.get_data_dir() / "snapshots" / "properties")
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def read_bundle_properties(self, bundle_path: Path) -> dict[str, str]:
        """Read system properties configured in a demo bundle."""
        return _load_bundle_properties(bundle_path)

    def load_snapshot(self, bundle_id: str, instance_id: str) -> PropertySnapshot | None:
        """Load an existing property snapshot for a bundle and instance."""
        target = _get_snapshot_path(self.snapshots_dir, bundle_id, instance_id)
        if not target.is_file():
            return None
        try:
            raw = json.loads(target.read_text(encoding="utf-8"))
            return PropertySnapshot.model_validate(raw)
        except Exception:
            return None

    def save_snapshot(self, snapshot: PropertySnapshot) -> Path:
        """Save a property snapshot to disk."""
        target = _get_snapshot_path(self.snapshots_dir, snapshot.bundle_id, snapshot.instance_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
        return target

    def delete_snapshot(self, bundle_id: str, instance_id: str) -> bool:
        """Delete an existing snapshot file upon successful restoration."""
        target = _get_snapshot_path(self.snapshots_dir, bundle_id, instance_id)
        if target.is_file():
            target.unlink()
            return True
        return False

    async def _query_single_property(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        auth: Any,
        name: str,
    ) -> tuple[str | None, str | None]:
        """Query Table API for a property sys_id and existing value."""
        url = f"{base_url}/api/now/table/sys_properties?sysparm_query=name={name}&sysparm_limit=1"
        resp = await client.get(url, auth=auth, headers={"Accept": "application/json"})
        if resp.status_code == 200:
            res = resp.json().get("result", [])
            if isinstance(res, list) and len(res) > 0:
                rec = res[0]
                return rec.get("sys_id"), rec.get("value")
        return None, None

    async def _update_or_insert_property(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        auth: Any,
        name: str,
        value: str,
        sys_id: str | None,
    ) -> bool:
        """Update existing sys_properties record or insert a new one."""
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if sys_id:
            url = f"{base_url}/api/now/table/sys_properties/{sys_id}"
            resp = await client.patch(url, auth=auth, headers=headers, json={"value": value})
            return resp.status_code in (200, 204)

        url = f"{base_url}/api/now/table/sys_properties"
        resp = await client.post(
            url, auth=auth, headers=headers, json={"name": name, "value": value}
        )
        return resp.status_code in (200, 201)

    async def apply_bundle_properties(
        self,
        bundle_id: str,
        bundle_path: Path,
        instance: InstanceRecord,
        client: httpx.AsyncClient | None = None,
        fake_mode: bool = False,
    ) -> PropertyApplyResult:
        """Snapshot current property values and apply bundle properties."""
        props = _load_bundle_properties(bundle_path)
        if not props:
            return PropertyApplyResult(
                success=True,
                applied_count=0,
                details=["No system properties configured for this bundle."],
            )

        if (
            fake_mode
            or instance.url.startswith("fake://")
            or instance.url.startswith("http://fake")
        ):
            simulated_snapshot = PropertySnapshot(
                bundle_id=bundle_id,
                instance_id=instance.id,
                timestamp=datetime.now(UTC).isoformat(),
                original_values={k: f"old_{k}" for k in props},
            )
            self.save_snapshot(simulated_snapshot)
            return PropertyApplyResult(
                success=True,
                applied_count=len(props),
                details=[f"Simulated setting {k}={v}" for k, v in props.items()],
            )

        base_url = instance.url.rstrip("/")
        auth = _build_auth(instance)
        original_vals: dict[str, str | None] = {}
        applied: list[str] = []
        failed: list[str] = []

        try:
            async with client or httpx.AsyncClient(timeout=10.0) as session:
                for name, new_val in props.items():
                    sys_id, cur_val = await self._query_single_property(
                        session, base_url, auth, name
                    )
                    original_vals[name] = cur_val
                    ok = await self._update_or_insert_property(
                        session, base_url, auth, name, new_val, sys_id
                    )
                    if ok:
                        applied.append(f"Set '{name}' = '{new_val}'")
                    else:
                        failed.append(f"Failed to update '{name}'")

            snapshot = PropertySnapshot(
                bundle_id=bundle_id,
                instance_id=instance.id,
                timestamp=datetime.now(UTC).isoformat(),
                original_values=original_vals,
            )
            self.save_snapshot(snapshot)
            return PropertyApplyResult(
                success=not failed,
                applied_count=len(applied),
                details=applied + failed,
            )
        except Exception as exc:
            return PropertyApplyResult(
                success=False,
                applied_count=0,
                details=[f"Error applying properties: {exc}"],
            )

    async def restore_properties(
        self,
        bundle_id: str,
        instance: InstanceRecord,
        client: httpx.AsyncClient | None = None,
        fake_mode: bool = False,
    ) -> PropertyApplyResult:
        """Restore previous property states from snapshot."""
        snapshot = self.load_snapshot(bundle_id, instance.id)
        if not snapshot:
            return PropertyApplyResult(
                success=True,
                applied_count=0,
                restored_count=0,
                details=["No active property snapshot found for this bundle and instance."],
            )

        if (
            fake_mode
            or instance.url.startswith("fake://")
            or instance.url.startswith("http://fake")
        ):
            self.delete_snapshot(bundle_id, instance.id)
            count = len(snapshot.original_values)
            return PropertyApplyResult(
                success=True,
                applied_count=0,
                restored_count=count,
                details=[f"Simulated restoring {k}" for k in snapshot.original_values],
            )

        base_url = instance.url.rstrip("/")
        auth = _build_auth(instance)
        restored: list[str] = []

        try:
            async with client or httpx.AsyncClient(timeout=10.0) as session:
                for name, old_val in snapshot.original_values.items():
                    if old_val is None:
                        continue
                    sys_id, _ = await self._query_single_property(session, base_url, auth, name)
                    ok = await self._update_or_insert_property(
                        session, base_url, auth, name, old_val, sys_id
                    )
                    if ok:
                        restored.append(f"Restored '{name}' to '{old_val}'")

            self.delete_snapshot(bundle_id, instance.id)
            return PropertyApplyResult(
                success=True,
                applied_count=0,
                restored_count=len(restored),
                details=restored,
            )
        except Exception as exc:
            return PropertyApplyResult(
                success=False,
                applied_count=0,
                restored_count=0,
                details=[f"Error restoring properties: {exc}"],
            )
