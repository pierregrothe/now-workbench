# tests/test_sharing.py
# Groups, approved shares and versions across several signed-in people (PRD-003, ADR-018).
# Author: Pierre Grothe
# Date: 2026-11-06
"""End-to-end sharing tests over the HTTP API."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from access_kit import as_user, multi_user_client
from fastapi.testclient import TestClient

ADMIN, ANA, BEN, CAL = (
    "admin@example.com",
    "ana@example.com",
    "ben@example.com",
    "cal@example.com",
)


def _write_bundle(root: Path, bundle_id: str, name: str) -> None:
    bundle = root / bundle_id
    (bundle / "seed").mkdir(parents=True)
    (bundle / "manifest.json").write_text(
        json.dumps({"id": bundle_id, "name": name, "description": "d"}), encoding="utf-8"
    )


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Admin owns the shipped 'starter' bundle; Ana, Ben and Cal are consultants."""
    bundles = tmp_path / "bundles"
    bundles.mkdir()
    monkeypatch.setenv("WORKBENCH_BUNDLES_DIR", str(bundles))
    _write_bundle(bundles, "starter", "Starter")
    with multi_user_client(ADMIN, (ANA, BEN, CAL)) as test_client:
        yield test_client


def _ids(client: TestClient, email: str) -> dict[str, dict[str, object]]:
    return {b["manifest"]["id"]: b for b in client.get("/api/demos", headers=as_user(email)).json()}


def _group(client: TestClient, name: str = "EMEA") -> str:
    res = client.post("/api/groups", json={"name": name, "kind": "region"}, headers=as_user(ADMIN))
    assert res.status_code == 200
    return str(res.json()["id"])


def test_list_demos_startup_bundles_belong_to_the_first_admin(client: TestClient) -> None:
    """Shipped bundles are the admin's; consultants see nothing until it is shared."""
    assert _ids(client, ADMIN)["starter"]["access"] == "owner"
    assert _ids(client, ANA) == {}
    assert client.get("/api/demos/starter", headers=as_user(ANA)).status_code == 404


def test_create_share_global_by_admin_is_approved_and_read_only(client: TestClient) -> None:
    """An admin's share with everyone needs no approval; recipients cannot change it."""
    res = client.post(
        "/api/artifacts/starter/shares", json={"target": "global"}, headers=as_user(ADMIN)
    )
    assert res.json()["status"] == "approved"
    seen = _ids(client, ANA)["starter"]
    assert seen["access"] == "shared"
    assert seen["owner_email"] == ADMIN
    rename = client.request("PATCH", "/api/demos/starter", json={"name": "x"}, headers=as_user(ANA))
    assert rename.status_code == 403
    assert client.delete("/api/demos/starter", headers=as_user(ANA)).status_code == 403
    assert (
        client.post(
            "/api/artifacts/starter/shares", json={"target": "global"}, headers=as_user(ANA)
        ).status_code
        == 404
    )


def test_clone_demo_bundle_from_a_share_gives_the_recipient_their_own_copy(
    client: TestClient,
) -> None:
    """Cloning a shared bundle creates one the recipient owns, at version 1."""
    client.post("/api/artifacts/starter/shares", json={"target": "global"}, headers=as_user(ADMIN))
    res = client.post(
        "/api/demos/starter/clone",
        json={"target_bundle_id": "ana-starter"},
        headers=as_user(ANA),
    )
    assert res.status_code == 200
    assert res.json()["access"] == "owner"
    assert res.json()["version"] == 1
    assert "ana-starter" not in _ids(client, ADMIN)


def test_create_share_with_group_waits_for_the_group_admin(client: TestClient) -> None:
    """A member's group share stays invisible until the group's administrator approves."""
    group = _group(client)
    client.put(f"/api/groups/{group}/members/{BEN}", json={"role": "admin"}, headers=as_user(ADMIN))
    assert client.post(f"/api/groups/{group}/join", headers=as_user(ANA)).json()["my_status"] == (
        "pending"
    )
    assert client.post(f"/api/groups/{group}/join", headers=as_user(CAL)).status_code == 200
    inbox = client.get("/api/approvals", headers=as_user(BEN)).json()
    assert {r["email"] for r in inbox["join_requests"]} == {ANA, CAL}
    for email in (ANA, CAL):
        client.put(f"/api/groups/{group}/members/{email}", json={}, headers=as_user(BEN))

    client.post("/api/artifacts/starter/shares", json={"target": "global"}, headers=as_user(ADMIN))
    client.post(
        "/api/demos/starter/clone", json={"target_bundle_id": "ana-demo"}, headers=as_user(ANA)
    )
    share = client.post(
        "/api/artifacts/ana-demo/shares",
        json={"target": "group", "group_id": group},
        headers=as_user(ANA),
    ).json()
    assert share["status"] == "pending"
    assert "ana-demo" not in _ids(client, CAL)
    cal_try = client.post(
        f"/api/approvals/shares/{share['id']}", json={"approve": True}, headers=as_user(CAL)
    )
    assert cal_try.status_code == 403
    decided = client.post(
        f"/api/approvals/shares/{share['id']}", json={"approve": True}, headers=as_user(BEN)
    )
    assert decided.json()["status"] == "approved"
    assert _ids(client, CAL)["ana-demo"]["version"] == 1


def test_create_version_needs_new_approval_and_recipients_keep_the_old_one(
    client: TestClient,
) -> None:
    """v2 of a shared artifact waits for approval; recipients stay on v1 until then."""
    group = _group(client)
    client.put(f"/api/groups/{group}/members/{BEN}", json={"role": "admin"}, headers=as_user(ADMIN))
    client.put(f"/api/groups/{group}/members/{ANA}", json={}, headers=as_user(ADMIN))
    client.put(f"/api/groups/{group}/members/{CAL}", json={}, headers=as_user(ADMIN))
    client.post("/api/artifacts/starter/shares", json={"target": "global"}, headers=as_user(ADMIN))
    client.post(
        "/api/demos/starter/clone", json={"target_bundle_id": "ana-demo"}, headers=as_user(ANA)
    )
    first = client.post(
        "/api/artifacts/ana-demo/shares",
        json={"target": "group", "group_id": group},
        headers=as_user(ANA),
    ).json()
    client.post(
        f"/api/approvals/shares/{first['id']}", json={"approve": True}, headers=as_user(BEN)
    )

    client.request("PATCH", "/api/demos/ana-demo", json={"name": "Renamed"}, headers=as_user(ANA))
    v2 = client.post(
        "/api/artifacts/ana-demo/versions", json={"note": "renamed"}, headers=as_user(ANA)
    ).json()
    assert v2["version"] == 2
    second = client.post(
        "/api/artifacts/ana-demo/shares",
        json={"target": "group", "group_id": group},
        headers=as_user(ANA),
    ).json()
    assert second["version"] == 2
    still = _ids(client, CAL)["ana-demo"]
    assert still["version"] == 1
    assert still["manifest"]["name"] != "Renamed"

    client.post(
        f"/api/approvals/shares/{second['id']}", json={"approve": True}, headers=as_user(BEN)
    )
    now = _ids(client, CAL)["ana-demo"]
    assert now["version"] == 2
    assert now["manifest"]["name"] == "Renamed"


def test_put_member_group_admin_cannot_appoint_admins(client: TestClient) -> None:
    """Only workbench administrators appoint group administrators."""
    group = _group(client)
    client.put(f"/api/groups/{group}/members/{BEN}", json={"role": "admin"}, headers=as_user(ADMIN))
    res = client.put(
        f"/api/groups/{group}/members/{ANA}", json={"role": "admin"}, headers=as_user(BEN)
    )
    assert res.status_code == 403


def test_create_group_needs_admin(client: TestClient) -> None:
    """Consultants cannot create groups."""
    res = client.post("/api/groups", json={"name": "X", "kind": "territory"}, headers=as_user(ANA))
    assert res.status_code == 403


def test_create_share_with_a_group_you_are_not_in_is_refused(client: TestClient) -> None:
    """A consultant cannot push an artifact into someone else's group."""
    group = _group(client)
    client.post("/api/artifacts/starter/shares", json={"target": "global"}, headers=as_user(ADMIN))
    client.post(
        "/api/demos/starter/clone", json={"target_bundle_id": "ana-demo"}, headers=as_user(ANA)
    )
    res = client.post(
        "/api/artifacts/ana-demo/shares",
        json={"target": "group", "group_id": group},
        headers=as_user(ANA),
    )
    assert res.status_code == 403


def test_withdraw_share_removes_access(client: TestClient) -> None:
    """The owner can stop sharing at any time."""
    share = client.post(
        "/api/artifacts/starter/shares", json={"target": "global"}, headers=as_user(ADMIN)
    ).json()
    assert "starter" in _ids(client, ANA)
    res = client.delete(f"/api/artifacts/starter/shares/{share['id']}", headers=as_user(ADMIN))
    assert res.status_code == 200
    assert "starter" not in _ids(client, ANA)


def test_delete_demo_by_owner_removes_shares_and_snapshots(client: TestClient) -> None:
    """Deleting the original takes the shared copies away too."""
    client.post("/api/artifacts/starter/shares", json={"target": "global"}, headers=as_user(ADMIN))
    assert client.delete("/api/demos/starter", headers=as_user(ADMIN)).status_code == 200
    assert _ids(client, ANA) == {}


def test_remove_member_leave_and_group_delete(client: TestClient) -> None:
    """People can leave; administrators can delete a group."""
    group = _group(client)
    client.put(f"/api/groups/{group}/members/{ANA}", json={}, headers=as_user(ADMIN))
    assert client.delete(f"/api/groups/{group}/members/{ANA}", headers=as_user(ANA)).json() == {
        "removed": True
    }
    assert client.delete(
        f"/api/groups/{group}/members/{BEN}", headers=as_user(ANA)
    ).status_code == (403)
    assert client.delete(f"/api/groups/{group}", headers=as_user(ADMIN)).status_code == 200
    assert client.get("/api/groups", headers=as_user(ANA)).json() == []
