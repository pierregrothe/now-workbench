"""Transactional seed record loader and rollback tracker for ServiceNow bundles."""

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

import httpx

from now_workbench.domains.instances import InstanceRecord, InstanceRepository, is_simulated
from now_workbench.domains.seed.date_wizard import transform_dataset_dates
from now_workbench.domains.seed.models import SeedOperationRecord, SeedRecordItem
from now_workbench.domains.seed.repository import SeedRepository


class SeedPayloadError(ValueError):
    """Raised when a bundle seed file cannot be read or parsed."""


class SeedEngine:
    """Manages transactional loading and rolling back of demo seed records."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        fake_mode: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.instances = InstanceRepository(conn)
        self.seeds = SeedRepository(conn)
        self.fake_mode = fake_mode
        self.transport = transport

    def _resolve_instance(self, instance_id: str | None) -> InstanceRecord:
        """Resolve target instance record or raise an error."""
        if instance_id:
            inst = self.instances.get_instance(instance_id)
            if not inst:
                raise ValueError(f"Instance '{instance_id}' not found in registry.")
            return inst

        inst = self.instances.get_default_instance()
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
            except Exception as exc:
                raise SeedPayloadError(f"Invalid seed file '{file_path.name}': {exc}") from exc
        return payloads

    async def _post_record(
        self,
        client: httpx.AsyncClient,
        inst: InstanceRecord,
        table: str,
        fields: dict[str, Any],
    ) -> str:
        """Create a single record in ServiceNow Table API (simulated per ``is_simulated``)."""
        if is_simulated(inst, self.fake_mode):
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
        """Delete a single record from ServiceNow Table API (simulated per ``is_simulated``)."""
        if is_simulated(inst, self.fake_mode):
            return True

        url = f"{inst.url.rstrip('/')}/api/now/table/{table}/{sys_id}"
        auth: Any = (
            httpx.BasicAuth(inst.username, inst.password)
            if inst.auth_type == "basic"
            else httpx.USE_CLIENT_DEFAULT
        )
        headers = {"Accept": "application/json"}

        resp = await client.delete(url, auth=auth, headers=headers, timeout=15.0)
        # 404 means the record is already gone (e.g. deleted by an earlier partial rollback).
        return resp.status_code in (200, 204, 404)

    async def load_and_seed(
        self,
        bundle_id: str,
        bundle_path: Path,
        instance_id: str | None = None,
        table_map: dict[str, str] | None = None,
    ) -> SeedOperationRecord:
        """Load and seed records from bundle seed directory into target instance.

        Args:
            bundle_id: Bundle id.
            bundle_path: Bundle directory.
            instance_id: Target instance (default when None).
            table_map: Table renames from a deployed Fluent app (ADR-022).
        """
        inst = self._resolve_instance(instance_id)
        seed_dir = bundle_path / "seed"
        renames = table_map or {}
        payloads = [
            (renames.get(table, table), fields)
            for table, fields in self._read_seed_payloads(seed_dir)
        ]

        if not payloads:
            raise ValueError(f"No seed records found in {seed_dir}")

        op_id = f"seed-{uuid.uuid4().hex[:8]}"
        created: list[SeedRecordItem] = []

        failure: Exception | None = None
        try:
            async with httpx.AsyncClient(transport=self.transport) as client:
                for table, fields in payloads:
                    sys_id = await self._post_record(client, inst, table, fields)
                    created.append(SeedRecordItem(table=table, sys_id=sys_id))
        except Exception as exc:
            failure = exc

        # Always persist, even on failure, so records already created keep a rollback handle.
        op = SeedOperationRecord(
            id=op_id,
            bundle_id=bundle_id,
            instance_id=inst.id,
            status="failed" if failure else "completed",
            created_records=created,
            error=str(failure)[:500] if failure else "",
        )
        self.seeds.record_seed_operation(op)
        if failure:
            raise RuntimeError(
                f"Seed operation '{op_id}' failed after {len(created)} record(s) were created "
                f"(roll back with operation id '{op_id}'): {failure}"
            ) from failure
        return op

    async def verify(self, operation_id: str) -> list[tuple[SeedRecordItem, bool, str]]:
        """Check, read-only, that each record a seed run created still exists on the instance.

        Returns:
            One ``(record, exists, detail)`` per created record.

        Raises:
            ValueError: The operation is unknown.
        """
        op = self.seeds.get_seed_operation(operation_id)
        if not op:
            raise ValueError(f"Seed operation '{operation_id}' not found.")
        inst = None if self.fake_mode else self._resolve_instance(op.instance_id)
        if inst is None or is_simulated(inst, self.fake_mode):
            return [(item, True, "simulated") for item in op.created_records]
        auth: Any = (
            httpx.BasicAuth(inst.username, inst.password)
            if inst.auth_type == "basic"
            else httpx.USE_CLIENT_DEFAULT
        )
        out: list[tuple[SeedRecordItem, bool, str]] = []
        async with httpx.AsyncClient(transport=self.transport) as client:
            for item in op.created_records:
                url = f"{inst.url.rstrip('/')}/api/now/table/{item.table}/{item.sys_id}"
                try:
                    resp = await client.get(
                        url,
                        auth=auth,
                        params={"sysparm_fields": "sys_id,number,short_description"},
                        headers={"Accept": "application/json"},
                        timeout=15.0,
                    )
                except httpx.HTTPError as exc:
                    out.append((item, False, f"could not ask the instance: {exc}"))
                    continue
                if resp.status_code == 200:
                    row = resp.json().get("result", {})
                    out.append((item, True, str(row.get("number") or row.get("sys_id", ""))))
                else:
                    out.append((item, False, f"HTTP {resp.status_code}"))
        return out

    async def rollback(self, operation_id: str) -> tuple[int, list[str]]:
        """Roll back (delete) all records created in a seed operation."""
        op = self.seeds.get_seed_operation(operation_id)
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

        # Only a fully successful rollback is final; otherwise stay retry-able.
        status = "rolled_back" if not errors else "rollback_failed"
        self.seeds.update_seed_operation_status(operation_id, status)
        return deleted_count, errors
