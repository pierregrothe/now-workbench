# tests/test_api_bundle_id_safety.py
# Every API route and engine that turns a bundle id into a path rejects unsafe ids with 400.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Route-level regression for deep-review sec-104.

BundleManager was fixed first; these tests cover the remaining routes and the engines
behind them (capture, pipeline, synthesizer), all of which now use ``safe_child`` and rely
on one ``UnsafePathError`` handler to answer HTTP 400 (never 500, never a filesystem hit).
"""

import pytest
from fastapi.testclient import TestClient

from now_workbench.api.app import create_app

# Valid as a URL path segment, but not valid bundle ids.
UNSAFE_IDS = [".hidden", "a..b", "x" * 129, "bad%20id"]

GET_ROUTES = [
    "/api/demos/{id}",
    "/api/demos/{id}/export",
    "/api/demos/{id}/runbook",
    "/api/demos/{id}/properties",
    "/api/demos/{id}/fluent",
    "/api/demos/{id}/captures",
    "/api/demos/{id}/evaluate",
]
DELETE_ROUTES = ["/api/demos/{id}", "/api/demos/{id}/captures"]
POST_ROUTES = [
    "/api/demos/{id}/build",
    "/api/demos/{id}/deploy",
    "/api/demos/{id}/reset",
    "/api/demos/{id}/properties/restore",
]


@pytest.fixture
def client() -> TestClient:
    """A test client over the real app (isolated data dir comes from conftest)."""
    return TestClient(create_app())


@pytest.mark.parametrize("bundle_id", UNSAFE_IDS)
@pytest.mark.parametrize("route", GET_ROUTES)
def test_get_routes_reject_unsafe_bundle_id(client: TestClient, route: str, bundle_id: str) -> None:
    """Read routes answer 400 for an id that cannot be a direct child of the bundles dir."""
    assert client.get(route.format(id=bundle_id)).status_code == 400


@pytest.mark.parametrize("bundle_id", UNSAFE_IDS)
@pytest.mark.parametrize("route", DELETE_ROUTES)
def test_delete_routes_reject_unsafe_bundle_id(
    client: TestClient, route: str, bundle_id: str
) -> None:
    """Destructive routes answer 400 before touching the filesystem."""
    assert client.delete(route.format(id=bundle_id)).status_code == 400


@pytest.mark.parametrize("bundle_id", UNSAFE_IDS)
@pytest.mark.parametrize("route", POST_ROUTES)
def test_post_routes_reject_unsafe_bundle_id(
    client: TestClient, route: str, bundle_id: str
) -> None:
    """Build, deploy, reset and restore routes answer 400 for unsafe ids."""
    assert client.post(route.format(id=bundle_id), json={}).status_code == 400


@pytest.mark.parametrize("filename", [".hidden", "a..b", "x" * 129])
def test_capture_file_route_rejects_unsafe_filename(client: TestClient, filename: str) -> None:
    """The media file name is validated too, not only the bundle id."""
    assert client.get(f"/api/demos/sample-ai-assistant/captures/{filename}").status_code == 400


def test_unknown_but_safe_bundle_id_is_still_not_found(client: TestClient) -> None:
    """A well-formed id that does not exist stays a 404, not a 400."""
    assert client.get("/api/demos/no-such-bundle").status_code == 404
