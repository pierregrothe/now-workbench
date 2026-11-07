# src/now_workbench/domains/instances/stats.py
# Live record counts from a ServiceNow instance through the Aggregate API (ADR-028).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Instance statistics.

Counts come from `GET /api/now/stats/<table>?sysparm_count=true`, read-only, a few requests
at a time. A count the instance refuses (no access, unknown table) is None, never zero, so a
chart cannot mistake "not allowed" for "empty" (ADR-013). A simulated instance has no
figures: asking for them is an error, not an invitation to invent some.
"""

import asyncio
from datetime import date, timedelta

import httpx

from now_workbench.domains.instances.connectivity import is_simulated
from now_workbench.domains.instances.models import InstanceRecord

__all__ = ["count_records", "daily_created"]

_PARALLEL = 6
_TIMEOUT = httpx.Timeout(15.0)
_COUNT = {"sysparm_count": "true"}
_HEADERS = {"Accept": "application/json"}


async def _count(
    http: httpx.AsyncClient, url: str, params: dict[str, str], gate: asyncio.Semaphore
) -> int | None:
    async with gate:
        try:
            res = await http.get(url, params=params)
        except httpx.HTTPError:
            return None
    if res.status_code != 200:
        return None
    try:
        return int(res.json()["result"]["stats"]["count"])
    except KeyError, TypeError, ValueError:
        return None


def _client(
    inst: InstanceRecord, fake_mode: bool, transport: httpx.AsyncBaseTransport | None
) -> httpx.AsyncClient:
    """An HTTP client for the instance; a simulated instance or workbench gets none."""
    if is_simulated(inst, fake_mode):
        raise ValueError(f"'{inst.name}' is a simulated instance; it has no live figures.")
    return httpx.AsyncClient(
        base_url=inst.url,
        auth=(inst.username, inst.password) if inst.auth_type == "basic" else None,
        headers=_HEADERS,
        timeout=_TIMEOUT,
        follow_redirects=True,
        transport=transport,
    )


async def count_records(
    inst: InstanceRecord,
    tables: list[str],
    fake_mode: bool = False,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, int | None]:
    """Count the records of each table on the instance.

    Args:
        inst: The instance (with credentials).
        tables: Table names, e.g. ["incident", "problem"].
        fake_mode: The workbench runs simulated; no instance is contacted.
        transport: HTTP transport override (tests).

    Returns:
        Count per table, None where the instance refused or failed.

    Raises:
        ValueError: The instance (or the workbench) is simulated.
    """
    gate = asyncio.Semaphore(_PARALLEL)
    async with _client(inst, fake_mode, transport) as http:
        counts = await asyncio.gather(
            *(_count(http, f"/api/now/stats/{t}", _COUNT, gate) for t in tables)
        )
    return {t: counts[i] for i, t in enumerate(tables)}


def _created_on(day: date) -> dict[str, str]:
    """Count parameters for the records created between this midnight and the next."""
    nxt = day + timedelta(days=1)
    query = f"sys_created_on>={day} 00:00:00^sys_created_on<{nxt} 00:00:00"
    return {**_COUNT, "sysparm_query": query}


async def daily_created(
    inst: InstanceRecord,
    table: str,
    days: list[date],
    fake_mode: bool = False,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[date, int | None]:
    """Count the records created on each day (days as the instance user's time zone sees them).

    Args:
        inst: The instance (with credentials).
        table: Table name.
        days: The days to count, oldest first.
        fake_mode: The workbench runs simulated; no instance is contacted.
        transport: HTTP transport override (tests).

    Returns:
        Count per day, None where the instance refused or failed.

    Raises:
        ValueError: The instance (or the workbench) is simulated.
    """
    gate = asyncio.Semaphore(_PARALLEL)
    async with _client(inst, fake_mode, transport) as http:
        counts = await asyncio.gather(
            *(_count(http, f"/api/now/stats/{table}", _created_on(d), gate) for d in days)
        )
    return {d: counts[i] for i, d in enumerate(days)}
