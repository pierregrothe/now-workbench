# tests/test_release_detection.py
# Tests for automatic ServiceNow release family detection (glide.war).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for release parsing, live detection, and check-and-record persistence."""

import httpx
import pytest

from now_workbench.connectivity import check_and_record_instance, detect_instance_release
from now_workbench.db import DatabaseRepository, InstanceCreate, init_db
from now_workbench.db.models import InstanceRecord
from now_workbench.releases import compare_releases, parse_release_family

# Real value read from a live Australia instance on 2026-11-06.
AUSTRALIA_WAR = "glide-australia-02-11-2026__patch7w42-10-08-2026_10-13-2026_1248.zip"


@pytest.mark.parametrize(
    ("build", "family"),
    [
        (AUSTRALIA_WAR, "Australia"),
        ("glide-zurich-07-01-2025__patch2-08-20-2025_1015.zip", "Zurich"),
        ("glide-washingtondc-12-20-2023__patch4.zip", "Washington DC"),
        ("glide-sandiego-12-22-2021__patch1.zip", "San Diego"),
        ("  GLIDE-XANADU-07-02-2024__patch3.zip ", "Xanadu"),
    ],
)
def test_parse_release_family_known_builds(build: str, family: str) -> None:
    """Build identifiers map to display family names."""
    assert parse_release_family(build) == family


@pytest.mark.parametrize("build", ["", "junk", "glide-zurich.zip", "war-zurich-07-01-2025"])
def test_parse_release_family_rejects_non_build_values(build: str) -> None:
    """Values that are not ServiceNow build identifiers yield None."""
    assert parse_release_family(build) is None


def test_compare_releases_australia_is_newest() -> None:
    """Australia orders after Zurich (it previously sorted lexically before Rome)."""
    assert compare_releases("Australia", "Zurich") == 1
    assert compare_releases("Australia", "Rome") == 1


def _instance(url: str = "https://acme.service-now.com") -> InstanceRecord:
    return InstanceRecord(id="i-1", name="Acme", url=url, username="admin", password="pw")


def _transport(
    war_status: int = 200, war_rows: list[dict[str, str]] | None = None
) -> httpx.MockTransport:
    """In-memory ServiceNow: incident probe succeeds, sys_properties returns glide.war."""
    rows = [{"value": AUSTRALIA_WAR}] if war_rows is None else war_rows

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/sys_properties"):
            assert request.url.params["sysparm_query"] == "name=glide.war"
            return httpx.Response(war_status, json={"result": rows})
        return httpx.Response(200, json={"result": []})

    return httpx.MockTransport(handler)


def test_detect_instance_release_reads_glide_war() -> None:
    """A readable glide.war property yields its family."""
    client = httpx.Client(transport=_transport())
    assert detect_instance_release(_instance(), client=client) == "Australia"


@pytest.mark.parametrize(("status", "rows"), [(403, []), (200, []), (200, [{"value": "x"}])])
def test_detect_instance_release_unavailable_returns_none(
    status: int, rows: list[dict[str, str]]
) -> None:
    """Forbidden, missing, or unparseable properties yield None (never a guess)."""
    client = httpx.Client(transport=_transport(status, rows))
    assert detect_instance_release(_instance(), client=client) is None


def test_detect_instance_release_network_error_returns_none() -> None:
    """Connection failures are swallowed into None."""

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    client = httpx.Client(transport=httpx.MockTransport(boom))
    assert detect_instance_release(_instance(), client=client) is None


def _repo_with_instance(url: str) -> tuple[DatabaseRepository, InstanceRecord]:
    repo = DatabaseRepository(init_db(":memory:"))
    inst = repo.add_instance(InstanceCreate(name="Acme", url=url, username="admin", password="pw"))
    return repo, inst


def test_check_and_record_instance_stores_detected_release() -> None:
    """A successful live check persists both status and the detected release."""
    repo, inst = _repo_with_instance("https://acme.service-now.com")
    assert inst.release == "Unknown"
    status, _, code = check_and_record_instance(repo, inst, transport=_transport())
    stored = repo.get_instance(inst.id)
    assert (status, code) == ("authenticated", 200)
    assert stored is not None and stored.release == "Australia"
    repo.close()


def test_check_and_record_instance_keeps_release_when_undetectable() -> None:
    """If glide.war is not readable, the stored release is left unchanged."""
    repo, inst = _repo_with_instance("https://acme.service-now.com")
    check_and_record_instance(repo, inst, transport=_transport(war_status=403))
    stored = repo.get_instance(inst.id)
    assert stored is not None and stored.release == "Unknown"
    assert stored.status == "authenticated"
    repo.close()


def test_check_and_record_instance_simulated_skips_detection() -> None:
    """fake:// instances never trigger a release lookup."""
    repo, inst = _repo_with_instance("fake://acme.service-now.com")
    status, _, _ = check_and_record_instance(repo, inst)
    stored = repo.get_instance(inst.id)
    assert status == "authenticated"
    assert stored is not None and stored.release == "Unknown"
    repo.close()
