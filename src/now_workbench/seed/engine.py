"""Transactional seed record loader and rollback tracker for ServiceNow bundles."""

import json
import uuid
from pathlib import Path
from typing import Any

import httpx

from now_workbench.db.models import (
    InstanceRecord,
    SeedOperationRecord,
    SeedRecordItem,
)
from now_workbench.db.repository import DatabaseRepository
from now_workbench.seed.date_wizard import transform_dataset_dates


class SeedEngine:
    """Manages transactional loading and rolling back of demo seed records."""

    def __init__(
        self,
        repository: DatabaseRepository,
        fake_mode: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.repo = repository
        self.fake_mode = fake_mode
        self.transport = transport

    def _resolve_instance(self, instance_id: str | None) -> InstanceRecord:
        """Resolve target instance record or raise an error."""
        if instance_id:
            inst = self.repo.get_instance(instance_id)
            if not inst:
                raise ValueError(f"Instance '{instance_id}' not found in registry.")
            return inst

        inst = self.repo.get_default_instance()
        if not inst:
            raise ValueError("No active default instance configured in registry.")
        return inst

    def _read_seed_payloads(self, seed_dir: Path) -> list[tuple[str, dict[str, Any]]]:
        """Read and sort seed JSON files from bundle seed directory."""
        if not seed_dir.exists():
            return []

        payloads: list[tuple[str, dict[str, Any]]] = []
        for file_path in sorted(seed_dir.glob("*.json")):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        table = item.get("table", "incident")
                        raw_fields = item.get("fields") or item.get("data", {})
                        fields = transform_dataset_dates(raw_fields)
                        payloads.append((table, fields))
            except Exception:
                continue
        return payloads

    async def _post_record(
        self,
        client: httpx.AsyncClient,
        inst: InstanceRecord,
        table: str,
        fields: dict[str, Any],
    ) -> str:
        """Create a single record in ServiceNow Table API."""
        if self.fake_mode:
            return f"fake_sys_{uuid.uuid4().hex[:16]}"

        url = f"{inst.url.rstrip('/')}/api/now/table/{table}"
        auth: Any = (
            httpx.BasicAuth(inst.username, inst.password)
            if inst.auth_type == "basic"
            else httpx.USE_CLIENT_DEFAULT
        )
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        resp = await client.post(url, auth=auth, headers=headers, json=fields, timeout=15.0)
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Failed to seed record in '{table}': HTTP {resp.status_code} - {resp.text[:120]}"
            )
        data = resp.json()
        sys_id = data.get("result", {}).get("sys_id")
        if not sys_id:
            raise RuntimeError(f"Table API response missing sys_id in '{table}'")
        return str(sys_id)

    async def _delete_record(
        self,
        client: httpx.AsyncClient,
        inst: InstanceRecord,
        table: str,
        sys_id: str,
    ) -> bool:
        """Delete a single record from ServiceNow Table API during rollback."""
        if self.fake_mode:
            return True

        url = f"{inst.url.rstrip('/')}/api/now/table/{table}/{sys_id}"
        auth: Any = (
            httpx.BasicAuth(inst.username, inst.password)
            if inst.auth_type == "basic"
            else httpx.USE_CLIENT_DEFAULT
        )
        headers = {"Accept": "application/json"}

        resp = await client.delete(url, auth=auth, headers=headers, timeout=15.0)
        return resp.status_code in (200, 204)

    async def load_and_seed(
        self,
        bundle_id: str,
        bundle_path: Path,
        instance_id: str | None = None,
    ) -> SeedOperationRecord:
        """Load and seed records from bundle seed directory into target instance."""
        inst = self._resolve_instance(instance_id)
        seed_dir = bundle_path / "seed"
        payloads = self._read_seed_payloads(seed_dir)

        if not payloads:
            raise ValueError(f"No seed records found in {seed_dir}")

        op_id = f"seed-{uuid.uuid4().hex[:8]}"
        created: list[SeedRecordItem] = []

        async with httpx.AsyncClient(transport=self.transport) as client:
            for table, fields in payloads:
                sys_id = await self._post_record(client, inst, table, fields)
                created.append(SeedRecordItem(table=table, sys_id=sys_id))

        op = SeedOperationRecord(
            id=op_id,
            bundle_id=bundle_id,
            instance_id=inst.id,
            status="completed",
            created_records=created,
        )
        self.repo.record_seed_operation(op)
        return op

    async def rollback(self, operation_id: str) -> tuple[int, list[str]]:
        """Roll back (delete) all records created in a seed operation."""
        op = self.repo.get_seed_operation(operation_id)
        if not op:
            raise ValueError(f"Seed operation '{operation_id}' not found.")
        if op.status == "rolled_back":
            raise ValueError(f"Seed operation '{operation_id}' has already been rolled back.")

        inst = self._resolve_instance(op.instance_id)
        deleted_count = 0
        errors: list[str] = []

        async with httpx.AsyncClient(transport=self.transport) as client:
            for item in reversed(op.created_records):
                try:
                    ok = await self._delete_record(client, inst, item.table, item.sys_id)
                    if ok:
                        deleted_count += 1
                    else:
                        errors.append(f"Could not delete {item.table}/{item.sys_id}")
                except Exception as exc:
                    errors.append(f"Error deleting {item.table}/{item.sys_id}: {exc}")

        self.repo.update_seed_operation_status(operation_id, "rolled_back")
        return deleted_count, errors
