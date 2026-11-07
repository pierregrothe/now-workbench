# tests/test_instance_profile.py
# Tests for platform profile detection at connection time (ADR-014).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for profile parsing, collection, persistence, and release ordering."""

import sqlite3
from datetime import UTC, datetime

import httpx
import pytest

from now_workbench.connectivity import check_and_record_instance
from now_workbench.db import (
    InstanceCreate,
    InstanceNode,
    InstanceProfile,
    InstanceUpdate,
    init_db,
)
from now_workbench.db.models import InstanceRecord
from now_workbench.db.repos.instances import InstanceRepository
from now_workbench.instance_profile import (
    collect_instance_profile,
    datacenter_from_hostname,
    parse_build_date,
    parse_node_stats,
)
from now_workbench.releases import (
    compare_releases,
    evaluate_release_prerequisites,
    is_release_compatible,
    parse_release_family,
)

WAR = "glide-australia-02-11-2026__patch7w42-10-08-2026_10-13-2026_1248.zip"

# Synthetic node diagnostics shaped like sys_cluster_node_stats.stats. The duplicated
# system.memory.max with type="info" mirrors the real payload: the live value must win.
STATS_XML = """<?xml version="1.0" encoding="UTF-8"?><xmlstats version="2">
<scheduler.memory.pressure.state>NOMINAL</scheduler.memory.pressure.state>
<db.product_name>MySQL</db.product_name>
<db.product_version>5.8.20-MariaDB-log</db.product_version>
<system.memory.max>2028.0</system.memory.max>
<system.memory.in.use>1374.0</system.memory.in.use>
<instance_type>dev</instance_type>
<servlet.uptime>3600000</servlet.uptime>
<glide.build.name>Australia</glide.build.name>
<glide.build.date>10-13-2026_1248</glide.build.date>
<glide.build.tag>glide-australia-02-11-2026__patch7w42-10-08-2026</glide.build.tag>
<system.memory.max type="info">1820.0</system.memory.max>
<system.os.name type="info">Linux</system.os.name>
<system.os.version type="info">4.18.0</system.os.version>
<jvm.version>21.0.11</jvm.version>
<jvm.cpu.count>64.0</jvm.cpu.count>
</xmlstats>"""


def test_parse_node_stats_prefers_live_values() -> None:
    """The first untyped element wins over type="info" duplicates; info fills gaps."""
    stats = parse_node_stats(STATS_XML)
    assert stats["system.memory.max"] == "2028.0"
    assert stats["system.os.name"] == "Linux"
    assert stats["glide.build.name"] == "Australia"
    assert "db.user_name" not in stats


def test_parse_node_stats_invalid_xml_returns_empty() -> None:
    """Unparseable diagnostics degrade to an empty mapping."""
    assert parse_node_stats("<not-xml") == {}


@pytest.mark.parametrize(
    ("host", "dc"),
    [
        ("app148145.aus101.service-now.com", "aus101"),
        ("APP1.YYZ3.SERVICE-NOW.COM", "yyz3"),
        ("localhost", None),
        ("node.example.com", None),
    ],
)
def test_datacenter_from_hostname_cases(host: str, dc: str | None) -> None:
    """Datacenter is the second label of a ServiceNow node hostname."""
    assert datacenter_from_hostname(host) == dc


def test_parse_build_date_formats() -> None:
    """Build stamps convert to ISO dates; garbage yields None."""
    assert parse_build_date("10-13-2026_1248") == "2026-10-13"
    assert parse_build_date("nope") is None


@pytest.mark.parametrize(
    ("build", "family"),
    [
        (WAR, "Australia"),
        ("glide-washingtondc-12-20-2023__patch4.zip", "Washington DC"),
        ("glide-sandiego-12-22-2021__patch1.zip", "San Diego"),
        ("glide-brazil-08-01-2027__patch0.zip", "Brazil"),
    ],
)
def test_parse_release_family_fallback(build: str, family: str) -> None:
    """glide.war fallback names any release, including ones the code has never seen."""
    assert parse_release_family(build) == family


def test_parse_release_family_rejects_non_build() -> None:
    """Non-build values yield None."""
    assert parse_release_family("junk") is None


def test_release_ordering_needs_no_future_names() -> None:
    """Unlisted names rank newest; undetected never passes a requirement."""
    assert compare_releases("Brazil", "Australia") == 1
    assert compare_releases("Australia", "Rome") == 1
    assert is_release_compatible("Brazil", "Zurich") is True
    assert is_release_compatible("Unknown", "Rome") is False
    result = evaluate_release_prerequisites("Unknown", "Xanadu")
    assert result.is_compatible is False
    assert "not been detected" in result.reason


def _instance(url: str = "https://acme.service-now.com") -> InstanceRecord:
    return InstanceRecord(id="i-1", name="Acme", url=url, username="admin", password="pw")


def _servicenow(admin: bool = True, props: bool = True) -> httpx.MockTransport:
    """In-memory ServiceNow Table API; non-admins get 403 on the cluster tables."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/incident"):
            return httpx.Response(200, json={"result": []})
        if path.endswith("/sys_properties"):
            if not props:
                return httpx.Response(403)
            return httpx.Response(
                200,
                json={
                    "result": [
                        {"name": "glide.war", "value": WAR},
                        {"name": "glide.installation.production", "value": "false"},
                        {"name": "glide.installation.name", "value": "Acme Dev"},
                        {"name": "instance_name", "value": "acme"},
                    ]
                },
            )
        if not admin:
            return httpx.Response(403)
        if path.endswith("/sys_cluster_state"):
            rows = [
                {
                    "node_id": f"n{i}",
                    "system_id": f"app{i}.yyz3.service-now.com:acme00{i}",
                    "status": "online",
                    "build_name": "Australia",
                    "node_stats": f"s{i}",
                }
                for i in (1, 2)
            ]
            return httpx.Response(200, json={"result": rows})
        if path.endswith("/sys_cluster_node_stats"):
            assert request.url.params["sysparm_query"] == "sys_idINs1,s2"
            return httpx.Response(
                200,
                json={
                    "result": [{"sys_id": "s1", "stats": STATS_XML}, {"sys_id": "s2", "stats": ""}]
                },
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_collect_instance_profile_admin_reads_everything() -> None:
    """An admin account yields release, reported type, datacenter, and per-node resources."""
    profile = collect_instance_profile(_instance(), client=httpx.Client(transport=_servicenow()))
    assert profile is not None
    assert (profile.release, profile.instance_type, profile.production_property) == (
        "Australia",
        "dev",
        False,
    )
    assert profile.installation_name == "Acme Dev"
    assert profile.datacenter == "yyz3"
    assert profile.build_date == "2026-10-13"
    assert profile.platform_name == "acme"
    assert (profile.db_product, profile.java_version, profile.os) == (
        "MySQL",
        "21.0.11",
        "Linux 4.18.0",
    )
    assert len(profile.nodes) == 2
    first = profile.nodes[0]
    assert (first.hostname, first.cpu_count, first.memory_max_mb) == (
        "app1.yyz3.service-now.com",
        64,
        2028.0,
    )
    assert first.memory_pressure == "NOMINAL"
    assert first.started_at is not None and first.started_at < datetime.now(UTC)
    assert profile.nodes[1].cpu_count is None  # node without stats keeps facts it has


def test_collect_instance_profile_non_admin_falls_back_to_glide_war() -> None:
    """Without cluster-table access the release still comes from glide.war."""
    client = httpx.Client(transport=_servicenow(admin=False))
    profile = collect_instance_profile(_instance(), client=client)
    assert profile is not None
    assert profile.release == "Australia"
    assert profile.build_tag == WAR.removesuffix(".zip")
    assert profile.nodes == [] and profile.datacenter is None


def test_collect_instance_profile_nothing_readable_returns_none() -> None:
    """When nothing can be read, no profile is produced (existing data is kept)."""
    client = httpx.Client(transport=_servicenow(admin=False, props=False))
    assert collect_instance_profile(_instance(), client=client) is None


def test_collect_instance_profile_network_error_returns_none() -> None:
    """Connection failures yield None instead of raising."""

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    assert (
        collect_instance_profile(
            _instance(), client=httpx.Client(transport=httpx.MockTransport(boom))
        )
        is None
    )


def _repo_with_instance(url: str) -> tuple[sqlite3.Connection, InstanceRecord]:
    conn = init_db(":memory:")
    inst = InstanceRepository(conn).add_instance(
        InstanceCreate(name="Acme", url=url, username="admin", password="pw")
    )
    return conn, inst


def test_check_and_record_instance_stores_profile_and_release() -> None:
    """A live check persists the profile; the instance release is derived from it."""
    conn, inst = _repo_with_instance("https://acme.service-now.com")
    instance_repo = InstanceRepository(conn)
    assert inst.release == "Unknown"
    status, _, _ = check_and_record_instance(conn, inst, transport=_servicenow())
    stored = instance_repo.get_instance(inst.id)
    profile = instance_repo.get_instance_profile(inst.id)
    assert status == "authenticated"
    assert stored is not None and stored.release == "Australia"
    assert profile is not None and len(profile.nodes) == 2 and profile.production_property is False
    conn.close()


def test_check_and_record_instance_keeps_profile_when_unreadable() -> None:
    """A later check that reads nothing does not wipe the stored profile."""
    conn, inst = _repo_with_instance("https://acme.service-now.com")
    check_and_record_instance(conn, inst, transport=_servicenow())
    check_and_record_instance(conn, inst, transport=_servicenow(admin=False, props=False))
    stored = InstanceRepository(conn).get_instance(inst.id)
    assert stored is not None and stored.release == "Australia"
    conn.close()


def test_check_and_record_instance_simulated_never_profiles() -> None:
    """fake:// instances are never probed, so no facts are invented for them."""
    conn, inst = _repo_with_instance("fake://acme.service-now.com")
    instance_repo = InstanceRepository(conn)
    check_and_record_instance(conn, inst)
    assert instance_repo.get_instance_profile(inst.id) is None
    stored = instance_repo.get_instance(inst.id)
    assert stored is not None and stored.release == "Unknown"
    conn.close()


def test_save_instance_profile_replaces_nodes() -> None:
    """Saving a new profile replaces the previous node list entirely."""
    conn, inst = _repo_with_instance("https://acme.service-now.com")
    instance_repo = InstanceRepository(conn)
    node = InstanceNode(node_id="a", hostname="a.yyz3.service-now.com", status="online")
    instance_repo.save_instance_profile(
        InstanceProfile(instance_id=inst.id, release="Zurich", nodes=[node])
    )
    instance_repo.save_instance_profile(InstanceProfile(instance_id=inst.id, release="Australia"))
    profile = instance_repo.get_instance_profile(inst.id)
    assert profile is not None and profile.release == "Australia" and profile.nodes == []
    assert profile.production_property is None
    conn.close()


def test_update_instance_url_change_discards_profile() -> None:
    """Pointing an instance at a new URL drops facts that described the old system."""
    conn, inst = _repo_with_instance("https://acme.service-now.com")
    instance_repo = InstanceRepository(conn)
    check_and_record_instance(conn, inst, transport=_servicenow())
    instance_repo.update_instance(inst.id, InstanceUpdate(name="Acme Renamed"))
    assert instance_repo.get_instance_profile(inst.id) is not None
    instance_repo.update_instance(inst.id, InstanceUpdate(url="https://other.service-now.com"))
    assert instance_repo.get_instance_profile(inst.id) is None
    stored = instance_repo.get_instance(inst.id)
    assert stored is not None and stored.release == "Unknown"
    conn.close()


def test_delete_instance_cascades_profile_and_nodes() -> None:
    """Deleting an instance removes its profile and nodes via foreign-key cascade."""
    conn, inst = _repo_with_instance("https://acme.service-now.com")
    check_and_record_instance(conn, inst, transport=_servicenow())
    InstanceRepository(conn).delete_instance(inst.id)
    counts = [
        conn.execute(f"SELECT COUNT(*) FROM {t};").fetchone()[0]
        for t in ("instance_profiles", "instance_nodes")
    ]
    assert counts == [0, 0]
    conn.close()


def test_instances_api_includes_profile_without_password() -> None:
    """GET /api/instances returns the detected profile and never the password."""
    from fastapi.testclient import TestClient

    from now_workbench.api.app import create_app
    from now_workbench.db import db_session

    with db_session() as conn:
        inst = InstanceRepository(conn).add_instance(
            InstanceCreate(name="Profiled", url="https://p.service-now.com", password="S3cret")
        )
        check_and_record_instance(conn, inst, transport=_servicenow())
    listed = TestClient(create_app()).get("/api/instances").json()
    entry = next(i for i in listed if i["name"] == "Profiled")
    assert entry["release"] == "Australia"
    assert entry["profile"]["datacenter"] == "yyz3"
    assert len(entry["profile"]["nodes"]) == 2
    assert "S3cret" not in str(listed)


def test_collect_instance_profile_non_numeric_stats_are_dropped() -> None:
    """Malformed numeric diagnostics become None instead of failing the whole profile."""
    bad = STATS_XML.replace(
        "<jvm.cpu.count>64.0</jvm.cpu.count>", "<jvm.cpu.count>n/a</jvm.cpu.count>"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/sys_cluster_node_stats"):
            return httpx.Response(200, json={"result": [{"sys_id": "s1", "stats": bad}]})
        return _servicenow().handle_request(request)

    profile = collect_instance_profile(
        _instance(), client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    assert profile is not None
    assert profile.nodes[0].cpu_count is None
    assert profile.nodes[0].memory_max_mb == 2028.0


def test_instance_purpose_defaults_to_demo_and_is_independent_of_reported_type() -> None:
    """A demo instance that ServiceNow reports as "prod" stays a demo unless the owner says so."""
    conn, inst = _repo_with_instance("https://acme.service-now.com")
    instance_repo = InstanceRepository(conn)
    assert inst.purpose == "demo"
    instance_repo.save_instance_profile(
        InstanceProfile(instance_id=inst.id, instance_type="prod", production_property=True)
    )
    stored = instance_repo.get_instance(inst.id)
    assert stored is not None and stored.purpose == "demo"
    updated = instance_repo.update_instance(inst.id, InstanceUpdate(purpose="production"))
    assert updated is not None and updated.purpose == "production"
    renamed = instance_repo.update_instance(inst.id, InstanceUpdate(name="Acme 2"))
    assert renamed is not None and renamed.purpose == "production"
    conn.close()


def test_instances_api_purpose_validation_and_public_view() -> None:
    """The API accepts declared purposes, rejects others, and exposes purpose publicly."""
    from fastapi.testclient import TestClient

    from now_workbench.api.app import create_app

    client = TestClient(create_app())
    bad = client.post(
        "/api/instances",
        json={"name": "Bad", "url": "fake://bad.service-now.com", "purpose": "prod"},
    )
    assert bad.status_code == 422
    made = client.post(
        "/api/instances",
        json={"name": "Lab", "url": "fake://lab.service-now.com", "purpose": "test"},
    )
    assert made.status_code == 200 and made.json()["purpose"] == "test"
    changed = client.put(f"/api/instances/{made.json()['id']}", json={"purpose": "development"})
    assert changed.json()["purpose"] == "development"
