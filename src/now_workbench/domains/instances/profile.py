# src/now_workbench/domains/instances/profile.py
# Read an instance's platform profile (release, environment, datacenter, nodes) at connection.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Platform profile collection over the ServiceNow Table API (ADR-014).

Three read-only GETs, each best-effort (an account without admin rights still gets
whatever ``sys_properties`` exposes):

1. ``sys_properties``: build identifier, production property, installation and
   instance names.
2. ``sys_cluster_state``: one row per application node (hostname, status, release).
3. ``sys_cluster_node_stats``: per-node diagnostics XML (CPU, memory, DB, Java, OS).

Nothing here hardcodes release names: the release is whatever the platform reports.
"""

import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from now_workbench.domains.instances.models import InstanceNode, InstanceProfile, InstanceRecord
from now_workbench.domains.releases import BUILD_PROPERTY, parse_release_family

__all__ = [
    "collect_instance_profile",
    "datacenter_from_hostname",
    "parse_build_date",
    "parse_node_stats",
]

_PROPERTY_NAMES = (
    BUILD_PROPERTY,
    "glide.installation.production",
    "glide.installation.name",
    "instance_name",
)

# Diagnostics XML elements kept from sys_cluster_node_stats.stats.
_STAT_KEYS = (
    "glide.build.name",
    "glide.build.tag",
    "glide.build.date",
    "instance_type",
    "db.product_name",
    "db.product_version",
    "jvm.version",
    "jvm.cpu.count",
    "system.os.name",
    "system.os.version",
    "system.memory.max",
    "system.memory.in.use",
    "scheduler.memory.pressure.state",
    "servlet.uptime",
)


def datacenter_from_hostname(hostname: str) -> str | None:
    """Return the datacenter code of a node hostname.

    Args:
        hostname: e.g. ``app148145.aus101.service-now.com``.

    Returns:
        The second DNS label (``aus101``), or None for non-ServiceNow hostnames.
    """
    labels = hostname.lower().split(".")
    if len(labels) >= 4 and hostname.lower().endswith(".service-now.com"):
        return labels[1]
    return None


def parse_build_date(raw: str) -> str | None:
    """Convert a ``MM-DD-YYYY_HHMM`` build stamp to an ISO date (``YYYY-MM-DD``)."""
    try:
        return datetime.strptime(raw.strip()[:10], "%m-%d-%Y").date().isoformat()
    except ValueError:
        return None


def parse_node_stats(xml_text: str) -> dict[str, str]:
    """Extract the kept diagnostics from a node's stats XML.

    The XML repeats some keys with ``type="info"`` (static config); the first
    element *without* a type attribute is the live value and wins.

    Args:
        xml_text: Content of ``sys_cluster_node_stats.stats``.

    Returns:
        Mapping of kept key -> text value (missing keys are absent).
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {}
    found: dict[str, str] = {}
    for live_pass in (True, False):
        for el in root:
            if el.tag in _STAT_KEYS and el.tag not in found:
                if live_pass and "type" in el.attrib:
                    continue
                if el.text and el.text.strip():
                    found[el.tag] = el.text.strip()
    return found


def _to_float(value: str | None) -> float | None:
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def _table(
    client: httpx.Client, base: str, table: str, params: dict[str, str]
) -> list[dict[str, Any]]:
    """GET a Table API resource; any failure (403, network, bad JSON) yields []."""
    try:
        res = client.get(f"{base}/api/now/table/{table}", params=params)
        if res.status_code != 200:
            return []
        rows = res.json().get("result")
        return rows if isinstance(rows, list) else []
    except httpx.HTTPError, ValueError:
        return []


def _build_node(row: dict[str, Any], stats: dict[str, str], now: datetime) -> InstanceNode:
    hostname = str(row.get("system_id", "")).split(":")[0] or str(row.get("node_id", ""))
    uptime_ms = _to_float(stats.get("servlet.uptime"))
    cpu = _to_float(stats.get("jvm.cpu.count"))
    return InstanceNode(
        node_id=str(row.get("node_id") or hostname),
        hostname=hostname,
        datacenter=datacenter_from_hostname(hostname),
        status=str(row.get("status") or "unknown"),
        cpu_count=int(cpu) if cpu is not None else None,
        memory_max_mb=_to_float(stats.get("system.memory.max")),
        memory_in_use_mb=_to_float(stats.get("system.memory.in.use")),
        memory_pressure=stats.get("scheduler.memory.pressure.state"),
        started_at=now - timedelta(milliseconds=uptime_ms) if uptime_ms is not None else None,
    )


def _fetch_sources(
    http: httpx.Client, base: str
) -> tuple[dict[str, str], list[dict[str, Any]], dict[str, dict[str, str]]]:
    """Run the three read-only GETs: properties, cluster nodes, per-node diagnostics."""
    props = {
        str(r.get("name")): str(r.get("value", ""))
        for r in _table(
            http,
            base,
            "sys_properties",
            {"sysparm_query": "nameIN" + ",".join(_PROPERTY_NAMES), "sysparm_fields": "name,value"},
        )
    }
    cluster = _table(
        http,
        base,
        "sys_cluster_state",
        {
            "sysparm_fields": "node_id,system_id,status,build_name,node_stats",
            "sysparm_exclude_reference_link": "true",
        },
    )
    stat_ids = [str(r["node_stats"]) for r in cluster if r.get("node_stats")]
    if not stat_ids:
        return props, cluster, {}
    stat_rows = _table(
        http,
        base,
        "sys_cluster_node_stats",
        {"sysparm_query": "sys_idIN" + ",".join(stat_ids), "sysparm_fields": "sys_id,stats"},
    )
    stats = {str(r.get("sys_id")): parse_node_stats(str(r.get("stats", ""))) for r in stat_rows}
    return props, cluster, stats


def _assemble_profile(
    instance_id: str,
    props: dict[str, str],
    cluster: list[dict[str, Any]],
    stats_by_id: dict[str, dict[str, str]],
    now: datetime,
) -> InstanceProfile:
    """Combine the three sources; the platform's own build name wins for the release."""
    nodes = [_build_node(r, stats_by_id.get(str(r.get("node_stats")), {}), now) for r in cluster]
    first = next((s for s in stats_by_id.values() if s), {})
    war = props.get(BUILD_PROPERTY, "")
    release = (
        first.get("glide.build.name")
        or next((str(r["build_name"]) for r in cluster if r.get("build_name")), None)
        or (parse_release_family(war) if war else None)
    )
    datacenters = Counter(n.datacenter for n in nodes if n.datacenter)
    production = props.get("glide.installation.production")
    os_parts = [first.get("system.os.name"), first.get("system.os.version")]
    return InstanceProfile(
        instance_id=instance_id,
        release=release,
        build_tag=first.get("glide.build.tag") or (war.removesuffix(".zip") or None),
        build_date=parse_build_date(first.get("glide.build.date", "")),
        platform_name=props.get("instance_name") or None,
        installation_name=props.get("glide.installation.name") or None,
        instance_type=first.get("instance_type"),
        production_property=None if production is None else production.lower() == "true",
        datacenter=datacenters.most_common(1)[0][0] if datacenters else None,
        db_product=first.get("db.product_name"),
        db_version=first.get("db.product_version"),
        java_version=first.get("jvm.version"),
        os=" ".join(p for p in os_parts if p) or None,
        nodes=nodes,
        captured_at=now,
    )


def collect_instance_profile(
    inst: InstanceRecord,
    client: httpx.Client | None = None,
    timeout: float = 10.0,
) -> InstanceProfile | None:
    """Read the instance's platform profile.

    Args:
        inst: Instance with decrypted credentials.
        client: Optional preconfigured HTTP client (closed after use).
        timeout: Per-request timeout in seconds when no client is given.

    Returns:
        The profile, or None when nothing at all could be read (so an existing
        profile is never overwritten by an empty one).
    """
    http = client or httpx.Client(timeout=timeout)
    http.headers["Accept"] = "application/json"
    if inst.auth_type == "basic":
        http.auth = (inst.username, inst.password)
    now = datetime.now(UTC)
    with http:
        props, cluster, stats_by_id = _fetch_sources(http, inst.url.rstrip("/"))
    if not props and not cluster:
        return None
    return _assemble_profile(inst.id, props, cluster, stats_by_id, now)
