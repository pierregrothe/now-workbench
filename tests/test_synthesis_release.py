# tests/test_synthesis_release.py
# The synthesized bundle's release comes from the target instance, never from user input
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for resolve_synthesis_release and the synthesize route's release handling."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from now_workbench.api.app import create_app
from now_workbench.db import UNKNOWN_RELEASE, InstanceCreate, InstanceProfile, db_session
from now_workbench.synthesizer.engine import UseCaseSynthesizer
from now_workbench.synthesizer.models import UseCaseSynthesisRequest
from now_workbench.synthesizer.release import resolve_synthesis_release


def _add(repo, instance_id: str, release: str, default: bool = False) -> None:
    repo.add_instance(
        InstanceCreate(
            id=instance_id,
            name=instance_id,
            url=f"https://{instance_id}.service-now.com",
            is_default=default,
        )
    )
    repo.save_instance_profile(InstanceProfile(instance_id=instance_id, release=release))


def test_resolve_synthesis_release_explicit_value_wins(tmp_path: Path) -> None:
    """A release passed by the caller is used as-is."""
    with db_session(tmp_path / "t.db") as repo:
        _add(repo, "a", "Australia", default=True)
        assert resolve_synthesis_release(repo, "Xanadu", None) == "Xanadu"


def test_resolve_synthesis_release_uses_default_instance_profile(tmp_path: Path) -> None:
    """With no explicit value or instance id, the default instance's detected release applies."""
    with db_session(tmp_path / "t.db") as repo:
        _add(repo, "a", "Australia", default=True)
        assert resolve_synthesis_release(repo, None, None) == "Australia"


def test_resolve_synthesis_release_uses_named_instance(tmp_path: Path) -> None:
    """A named instance overrides the default instance."""
    with db_session(tmp_path / "t.db") as repo:
        _add(repo, "a", "Australia", default=True)
        _add(repo, "b", "Yokohama")
        assert resolve_synthesis_release(repo, None, "b") == "Yokohama"


def test_resolve_synthesis_release_unknown_instance_raises(tmp_path: Path) -> None:
    """An instance id that does not exist is an error, not a silent fallback."""
    with db_session(tmp_path / "t.db") as repo, pytest.raises(LookupError):
        resolve_synthesis_release(repo, None, "nope")


def test_resolve_synthesis_release_falls_back_to_saved_default(tmp_path: Path) -> None:
    """No instance, or an unknown release, falls back to the saved workbench default."""
    with db_session(tmp_path / "t.db") as repo:
        fallback = repo.get_workbench_preferences().default_sn_release
        assert resolve_synthesis_release(repo, None, None) == fallback
        _add(repo, "a", UNKNOWN_RELEASE, default=True)
        assert resolve_synthesis_release(repo, None, None) == fallback


def test_synthesize_engine_rejects_unresolved_release(tmp_path: Path) -> None:
    """The engine never stamps a bundle with a missing release."""
    req = UseCaseSynthesisRequest(use_case="Incident triage")
    with pytest.raises(ValueError, match="sn_release"):
        UseCaseSynthesizer(bundles_dir=tmp_path).synthesize(req)


def test_synthesize_route_stamps_default_instance_release() -> None:
    """The route builds the bundle for the default instance's detected release."""
    with db_session() as repo:
        _add(repo, "route-a", "Australia", default=True)
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
