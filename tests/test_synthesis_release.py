# tests/test_synthesis_release.py
# The synthesized bundle's release comes from the target instance, never from user input
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for resolve_synthesis_release and the synthesize route's release handling."""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from now_workbench.api.app import create_app
from now_workbench.db import UNKNOWN_RELEASE, InstanceCreate, InstanceProfile, db_session
from now_workbench.db.repos.instances import InstanceRepository
from now_workbench.synthesizer.engine import UseCaseSynthesizer
from now_workbench.synthesizer.models import UseCaseSynthesisRequest
from now_workbench.synthesizer.release import NoReleaseError, resolve_synthesis_release


def _add(conn: sqlite3.Connection, instance_id: str, release: str, default: bool = False) -> None:
    instances = InstanceRepository(conn)
    instances.add_instance(
        InstanceCreate(
            id=instance_id,
            name=instance_id,
            url=f"https://{instance_id}.service-now.com",
            is_default=default,
        )
    )
    instances.save_instance_profile(InstanceProfile(instance_id=instance_id, release=release))


def test_resolve_synthesis_release_explicit_value_wins(tmp_path: Path) -> None:
    """A release passed by the caller is used as-is."""
    with db_session(tmp_path / "t.db") as conn:
        _add(conn, "a", "Australia", default=True)
        assert resolve_synthesis_release(conn, "Xanadu", None) == "Xanadu"


def test_resolve_synthesis_release_uses_default_instance_profile(tmp_path: Path) -> None:
    """With no explicit value or instance id, the default instance's detected release applies."""
    with db_session(tmp_path / "t.db") as conn:
        _add(conn, "a", "Australia", default=True)
        assert resolve_synthesis_release(conn, None, None) == "Australia"


def test_resolve_synthesis_release_uses_named_instance(tmp_path: Path) -> None:
    """A named instance overrides the default instance."""
    with db_session(tmp_path / "t.db") as conn:
        _add(conn, "a", "Australia", default=True)
        _add(conn, "b", "Yokohama")
        assert resolve_synthesis_release(conn, None, "b") == "Yokohama"


def test_resolve_synthesis_release_unknown_instance_raises(tmp_path: Path) -> None:
    """An instance id that does not exist is an error, not a silent fallback."""
    with db_session(tmp_path / "t.db") as conn, pytest.raises(LookupError):
        resolve_synthesis_release(conn, None, "nope")


def test_resolve_synthesis_release_never_guesses(tmp_path: Path) -> None:
    """No instance, or an unknown release, raises instead of inventing a release."""
    with db_session(tmp_path / "t.db") as conn:
        with pytest.raises(NoReleaseError):
            resolve_synthesis_release(conn, None, None)
        _add(conn, "a", UNKNOWN_RELEASE, default=True)
        with pytest.raises(NoReleaseError):
            resolve_synthesis_release(conn, None, None)


def test_synthesize_engine_rejects_unresolved_release(tmp_path: Path) -> None:
    """The engine never stamps a bundle with a missing release."""
    req = UseCaseSynthesisRequest(use_case="Incident triage")
    with pytest.raises(ValueError, match="sn_release"):
        UseCaseSynthesizer(bundles_dir=tmp_path).synthesize(req)


def test_synthesize_route_stamps_default_instance_release() -> None:
    """The route builds the bundle for the default instance's detected release."""
    with db_session() as conn:
        _add(conn, "route-a", "Australia", default=True)
    client = TestClient(create_app())
    res = client.post("/api/demos/synthesize", json={"use_case": "Incident triage for release"})
    assert res.status_code == 200, res.text
    bundle_id = res.json()["bundle_id"]
    try:
        manifest = client.get(f"/api/demos/{bundle_id}").json()["manifest"]
        assert manifest["sn_release"] == "Australia"
    finally:
        client.delete(f"/api/demos/{bundle_id}")


def test_synthesize_route_unknown_instance_is_not_found() -> None:
    """An unknown instance id answers 404."""
    client = TestClient(create_app())
    res = client.post(
        "/api/demos/synthesize", json={"use_case": "Incident triage", "instance_id": "nope"}
    )
    assert res.status_code == 404


def test_synthesize_route_without_instance_is_conflict() -> None:
    """With no instance to take a release from, the route answers 409 and builds nothing."""
    client = TestClient(create_app())
    res = client.post("/api/demos/synthesize", json={"use_case": "Incident triage"})
    assert res.status_code == 409
