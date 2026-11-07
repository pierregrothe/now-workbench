# tests/test_impersonation.py
# Acting as someone else: who may, and every workload running as the impersonated person.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for ADR-020 impersonation over the HTTP API."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from access_kit import as_user, multi_user_client
from fastapi.testclient import TestClient

from now_workbench.db import db_session

ADMIN, ANA, BEN, CAL = (
    "admin@example.com",
    "ana@example.com",
    "ben@example.com",
    "cal@example.com",
)
_INSTANCE = {"name": "Ana Dev", "url": "fake://ana.service-now.com", "password": "p"}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Admin plus three consultants; Ben administers group G where Ana is a member."""
    bundles = tmp_path / "bundles"
    (bundles / "starter").mkdir(parents=True)
    (bundles / "starter" / "manifest.json").write_text(
        json.dumps({"id": "starter", "name": "Starter"}), encoding="utf-8"
    )
    monkeypatch.setenv("WORKBENCH_BUNDLES_DIR", str(bundles))
    with multi_user_client(ADMIN, (ANA, BEN, CAL)) as test_client:
        group = test_client.post(
            "/api/groups", json={"name": "Group G", "kind": "region"}, headers=as_user(ADMIN)
        ).json()["id"]
        for email, role in ((BEN, "admin"), (ANA, "member")):
            test_client.put(
                f"/api/groups/{group}/members/{email}", json={"role": role}, headers=as_user(ADMIN)
            )
        yield test_client


def _act_as(client: TestClient, real: str, target: str) -> int:
    return client.post(
        "/api/impersonation", json={"email": target}, headers=as_user(real)
    ).status_code


def test_start_impersonation_admin_may_act_as_anyone(client: TestClient) -> None:
    """A workbench administrator can act as any member."""
    status = client.get("/api/impersonation", headers=as_user(ADMIN)).json()
    assert status["candidates"] == [ANA, BEN, CAL]
    assert _act_as(client, ADMIN, CAL) == 200
    profile = client.get("/api/profile", headers=as_user(ADMIN)).json()
    assert profile["email"] == CAL
    assert profile["roles"] == ["solution_consultant"]


def test_start_impersonation_group_admin_only_their_members(client: TestClient) -> None:
    """A group admin may act as their group's members, not others and never an admin."""
    status = client.get("/api/impersonation", headers=as_user(BEN)).json()
    assert status["candidates"] == [ANA]
    assert _act_as(client, BEN, CAL) == 403
    assert _act_as(client, BEN, ADMIN) == 403
    assert _act_as(client, ANA, BEN) == 403
    assert _act_as(client, BEN, ANA) == 200


def test_start_impersonation_never_escalates_to_an_admin_member(client: TestClient) -> None:
    """Even when an administrator joins Ben's group, Ben cannot act as them."""
    group = client.get("/api/groups", headers=as_user(ADMIN)).json()[0]["id"]
    client.put(f"/api/groups/{group}/members/{ADMIN}", json={}, headers=as_user(ADMIN))
    assert _act_as(client, BEN, ADMIN) == 403


def test_impersonation_instances_threads_settings_run_as_the_target(client: TestClient) -> None:
    """Instances, conversations and settings created while acting belong to the target."""
    _act_as(client, ADMIN, ANA)
    created = client.post("/api/instances", json=_INSTANCE, headers=as_user(ADMIN)).json()
    thread = client.post(
        "/api/threads", json={"title": "Made for Ana"}, headers=as_user(ADMIN)
    ).json()
    client.put("/api/settings", json={"narrative_tone": "technical"}, headers=as_user(ADMIN))
    client.delete("/api/impersonation", headers=as_user(ADMIN))

    ana_instances = {i["id"] for i in client.get("/api/instances", headers=as_user(ANA)).json()}
    assert created["id"] in ana_instances
    admin_instances = {i["id"] for i in client.get("/api/instances", headers=as_user(ADMIN)).json()}
    assert created["id"] not in admin_instances
    ana_threads = {t["id"] for t in client.get("/api/threads", headers=as_user(ANA)).json()}
    assert thread["id"] in ana_threads
    ana_tone = client.get("/api/settings", headers=as_user(ANA)).json()["narrative_tone"]
    admin_tone = client.get("/api/settings", headers=as_user(ADMIN)).json()["narrative_tone"]
    assert (ana_tone, admin_tone) == ("technical", "executive")


def test_impersonation_bundles_and_admin_screens_follow_the_target(client: TestClient) -> None:
    """Acting as a consultant shows their library and denies admin-only screens."""
    _act_as(client, ADMIN, ANA)
    assert client.get("/api/demos", headers=as_user(ADMIN)).json() == []
    assert client.get("/api/team", headers=as_user(ADMIN)).status_code == 403
    assert client.get("/api/demos/starter", headers=as_user(ADMIN)).status_code == 404
    # Stopping always works, even with the target's (smaller) roles in force.
    assert client.delete("/api/impersonation", headers=as_user(ADMIN)).json()["acting_as"] is None
    assert client.get("/api/team", headers=as_user(ADMIN)).status_code == 200


def test_impersonation_approvals_are_the_targets(client: TestClient) -> None:
    """Acting as the group admin shows (and decides) that group admin's inbox."""
    client.post("/api/artifacts/starter/shares", json={"target": "global"}, headers=as_user(ADMIN))
    client.post(
        "/api/demos/starter/clone", json={"target_bundle_id": "ana-demo"}, headers=as_user(ANA)
    )
    group = client.get("/api/groups", headers=as_user(ANA)).json()[0]["id"]
    share = client.post(
        "/api/artifacts/ana-demo/shares",
        json={"target": "group", "group_id": group},
        headers=as_user(ANA),
    ).json()
    _act_as(client, ADMIN, BEN)
    inbox = client.get("/api/approvals", headers=as_user(ADMIN)).json()
    assert [s["id"] for s in inbox["shares"]] == [share["id"]]


def test_impersonation_otto_tools_act_on_the_targets_data(client: TestClient) -> None:
    """A confirmed Otto action while acting as Ana touches Ana's instances only."""
    mine = client.post(
        "/api/instances",
        json={**_INSTANCE, "name": "Admin Dev", "url": "fake://auth-failed.service-now.com"},
        headers=as_user(ADMIN),
    ).json()
    client.post(
        "/api/instances",
        json={**_INSTANCE, "url": "fake://auth-failed.service-now.com"},
        headers=as_user(ANA),
    )
    _act_as(client, ADMIN, ANA)
    thread = client.post("/api/threads", json={"title": "t"}, headers=as_user(ADMIN)).json()
    res = client.post(
        f"/api/threads/{thread['id']}/messages",
        json={
            "content": "Confirmed: delete Ana Dev",
            "role": "user",
            "widget_type": "tool_confirm",
            "widget_data": {"tool": "delete_instances", "input": {"instances": ["Ana Dev"]}},
        },
        headers=as_user(ADMIN),
    )
    assert "Deleted 1 instance" in res.json()[-1]["content"]
    client.delete("/api/impersonation", headers=as_user(ADMIN))
    assert mine["id"] in {
        i["id"] for i in client.get("/api/instances", headers=as_user(ADMIN)).json()
    }
    assert "Ana Dev" not in {
        i["name"] for i in client.get("/api/instances", headers=as_user(ANA)).json()
    }


def test_effective_user_revokes_when_rights_are_removed(client: TestClient) -> None:
    """Demoting the group admin ends their impersonation on the next request, logged."""
    _act_as(client, BEN, ANA)
    assert client.get("/api/profile", headers=as_user(BEN)).json()["email"] == ANA
    group = client.get("/api/groups", headers=as_user(ADMIN)).json()[0]["id"]
    client.put(
        f"/api/groups/{group}/members/{BEN}", json={"role": "member"}, headers=as_user(ADMIN)
    )
    assert client.get("/api/profile", headers=as_user(BEN)).json()["email"] == BEN
    with db_session() as conn:
        actions = [
            r["action"]
            for r in conn.execute(
                "SELECT action FROM impersonation_log WHERE real_email = ? ORDER BY id;", (BEN,)
            )
        ]
    assert actions == ["start", "revoked"]


def test_start_impersonation_uses_real_rights_while_acting(client: TestClient) -> None:
    """Switching target from inside an impersonation is judged on the signed-in admin."""
    _act_as(client, ADMIN, ANA)
    assert _act_as(client, ADMIN, CAL) == 200
    assert client.get("/api/impersonation", headers=as_user(ADMIN)).json()["acting_as"] == CAL


def test_start_impersonation_refuses_someone_not_on_the_team(client: TestClient) -> None:
    """Only members with a role can be impersonated."""
    assert _act_as(client, ADMIN, "stranger@example.com") == 403
