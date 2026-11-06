# tests/test_cov_api.py
# Coverage tests for the API, auth, sharing and repository layers (low-level units first).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Fill the remaining line-coverage gaps in api/, auth/, sharing/ and db/repos/."""

import shutil
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import jwt
import pytest
from access_kit import as_user, multi_user_client
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from now_workbench.auth.access import AccessValidator
from now_workbench.auth.guard import current_user
from now_workbench.auth.models import AuthUser
from now_workbench.auth.setup import SetupCodes, SetupError, TooManyAttemptsError
from now_workbench.bundles.manager import BundleManager
from now_workbench.bundles.pipeline import DemoPipelineEngine
from now_workbench.capture.engine import CaptureFailedError, PlaywrightCaptureEngine
from now_workbench.db import db_session
from now_workbench.sharing.access import sync_registry
from now_workbench.sharing.models import GroupKind, ShareTarget
from now_workbench.sharing.store import published_root, snapshot_bundle

# --- auth -------------------------------------------------------------------------------


def test_current_user_without_middleware_state_is_401() -> None:
    """A route using current_user without the auth middleware refuses the request."""
    app = FastAPI()

    @app.get("/who")
    def who(user: AuthUser = Depends(current_user)) -> str:
        return user.email

    res = TestClient(app).get("/who")
    assert res.status_code == 401
    assert res.json()["detail"] == "Not authenticated."


def test_setup_codes_clear_forgets_the_active_code() -> None:
    """clear() makes the holder inactive and redeem raises SetupError."""
    announced: list[str] = []
    codes = SetupCodes(announced.append)
    codes.issue()
    assert codes.active
    codes.clear()
    assert not codes.active
    with pytest.raises(SetupError, match="No setup code is active"):
        codes.redeem("AAAA-AAAA")


def test_setup_codes_redeem_accepts_the_announced_code_once() -> None:
    """The announced code redeems; a second use finds no active code."""
    announced: list[str] = []
    codes = SetupCodes(announced.append)
    codes.issue()
    codes.redeem(announced[0].lower())
    assert not codes.active
    with pytest.raises(SetupError):
        codes.redeem(announced[0])


def test_setup_codes_too_many_wrong_attempts_issue_a_new_code() -> None:
    """The fifth miss raises TooManyAttemptsError and announces a fresh code."""
    announced: list[str] = []
    codes = SetupCodes(announced.append)
    codes.issue()
    for _ in range(4):
        with pytest.raises(SetupError):
            codes.redeem("WRONG-CODE")
    with pytest.raises(TooManyAttemptsError):
        codes.redeem("WRONG-CODE")
    assert len(announced) == 2


def test_access_validator_without_resolver_fetches_jwks_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without an injected resolver the validator builds a JWKS client and caches it."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    built: list[str] = []

    class FakeSigningKey:
        def __init__(self, k: Any) -> None:
            self.key = k

    class FakeJWKClient:
        def __init__(self, url: str, cache_keys: bool = False) -> None:
            built.append(url)

        def get_signing_key_from_jwt(self, token: str) -> FakeSigningKey:
            return FakeSigningKey(key.public_key())

    monkeypatch.setattr("now_workbench.auth.access.PyJWKClient", FakeJWKClient)
    validator = AccessValidator("team.cloudflareaccess.com", "aud")
    now = int(time.time())
    token = jwt.encode(
        {
            "aud": "aud",
            "iss": "https://team.cloudflareaccess.com",
            "iat": now,
            "exp": now + 60,
            "email": "a@example.com",
        },
        key,
        algorithm="RS256",
    )
    assert validator.email(token) == "a@example.com"
    assert validator.email(token) == "a@example.com"
    assert built == ["https://team.cloudflareaccess.com/cdn-cgi/access/certs"]


# --- sharing store / registry -----------------------------------------------------------


def test_snapshot_bundle_twice_raises_file_exists(tmp_path: Path) -> None:
    """A version can be frozen only once."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "manifest.json").write_text("{}", encoding="utf-8")
    assert snapshot_bundle(src, "demo", 1) > 0
    with pytest.raises(FileExistsError):
        snapshot_bundle(src, "demo", 1)


def test_published_root_missing_version_raises_file_not_found() -> None:
    """Unpacking a version that was never frozen fails."""
    with pytest.raises(FileNotFoundError, match="missing"):
        published_root("ghost", 3)


def test_sync_registry_missing_bundles_dir_registers_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no bundles directory the registry sync adds nothing."""
    monkeypatch.setenv("WORKBENCH_BUNDLES_DIR", str(tmp_path / "nope"))
    with db_session() as repo:
        assert sync_registry(repo, "local@localhost") == 0


# --- repositories -----------------------------------------------------------------------


def test_repo_artifact_versions_and_shares_queries() -> None:
    """Version lookup, live share listing, decide errors and pending-share filters."""
    with db_session() as repo:
        repo.register_artifact("demo", "o@example.com")
        v = repo.add_artifact_version("demo", "Demo", "d", "n", 10, "o@example.com")
        assert repo.get_artifact_version("demo", v.version) is not None
        assert repo.get_artifact_version("demo", 99) is None
        grp = repo.create_group("EMEA", GroupKind.REGION, "", "o@example.com")
        share = repo.request_share("demo", v.version, ShareTarget.GROUP, grp.id, "o@example.com")
        assert [s.id for s in repo.list_artifact_shares("demo")] == [share.id]
        assert repo.list_artifact_shares("other") == []
        assert repo.pending_shares([], include_global=False) == []
        assert [s.id for s in repo.pending_shares([grp.id], include_global=False)] == [share.id]
        repo.decide_share(share.id, True, "o@example.com")
        with pytest.raises(LookupError):
            repo.decide_share(share.id, True, "o@example.com")
        with pytest.raises(LookupError):
            repo.decide_share("shr-missing", False, "o@example.com")


def test_repo_create_group_duplicate_name_raises_value_error() -> None:
    """A second group with the same name is refused."""
    with db_session() as repo:
        repo.create_group("EMEA", GroupKind.REGION, "", "o@example.com")
        with pytest.raises(ValueError, match="already exists"):
            repo.create_group("EMEA", GroupKind.REGION, "", "o@example.com")


def test_repo_pending_join_requests_empty_group_list_is_empty() -> None:
    """An empty group filter returns nothing, None returns every group's requests."""
    with db_session() as repo:
        grp = repo.create_group("EMEA", GroupKind.REGION, "", "o@example.com")
        repo.request_to_join(grp.id, "a@example.com")
        assert repo.pending_join_requests([]) == []
        assert [m.email for m in repo.pending_join_requests(None)] == ["a@example.com"]
        assert [m.email for m in repo.pending_join_requests([grp.id])] == ["a@example.com"]


def test_repo_end_impersonation_without_one_returns_false() -> None:
    """Ending an impersonation that does not exist is a no-op."""
    with db_session() as repo:
        assert repo.end_impersonation("a@example.com") is False
        repo.start_impersonation("a@example.com", "b@example.com")
        assert repo.end_impersonation("a@example.com", action="revoked") is True
        assert repo.get_impersonation("a@example.com") is None


# --- demos API (local mode) -------------------------------------------------------------

SAMPLE = Path(__file__).resolve().parent.parent / "bundles" / "sample-ai-assistant"
BID = "sample-ai-assistant"


@pytest.fixture
def demos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """A local-mode client whose bundles directory holds the sample bundle."""
    bundles = tmp_path / "bundles"
    bundles.mkdir()
    shutil.copytree(SAMPLE, bundles / BID)
    monkeypatch.setenv("WORKBENCH_BUNDLES_DIR", str(bundles))
    from now_workbench.api.app import create_app

    with TestClient(create_app()) as client:
        yield client


def _raiser(exc: Exception) -> Any:
    def fail(*_a: Any, **_k: Any) -> Any:
        raise exc

    return fail


def _araiser(exc: Exception) -> Any:
    async def fail(*_a: Any, **_k: Any) -> Any:
        raise exc

    return fail


def test_clone_demo_bundle_missing_source_file_is_404(
    demos: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A manager FileNotFoundError during clone maps to 404."""
    monkeypatch.setattr(BundleManager, "clone_bundle", _raiser(FileNotFoundError("gone")))
    res = demos.post(f"/api/demos/{BID}/clone", json={"target_bundle_id": "copy"})
    assert res.status_code == 404
    assert res.json()["detail"] == "gone"


def test_delete_demo_manager_errors_map_to_404_and_400(
    demos: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FileNotFoundError and ValueError from delete_bundle become 404 and 400."""
    monkeypatch.setattr(BundleManager, "delete_bundle", _raiser(FileNotFoundError("nf")))
    assert demos.delete(f"/api/demos/{BID}").status_code == 404
    monkeypatch.setattr(BundleManager, "delete_bundle", _raiser(ValueError("bad")))
    assert demos.delete(f"/api/demos/{BID}").status_code == 400


def test_update_demo_bundle_manager_errors_map_to_404_and_400(
    demos: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FileNotFoundError and ValueError from the manifest update become 404 and 400."""
    monkeypatch.setattr(BundleManager, "update_bundle_manifest", _raiser(FileNotFoundError("nf")))
    assert demos.request("PATCH", f"/api/demos/{BID}", json={"name": "x"}).status_code == 404
    monkeypatch.setattr(BundleManager, "update_bundle_manifest", _raiser(ValueError("bad")))
    assert demos.request("PATCH", f"/api/demos/{BID}", json={"name": "x"}).status_code == 400


def test_export_demo_failure_is_400(demos: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """An export that blows up is reported as 400 with the reason."""
    monkeypatch.setattr(BundleManager, "export_bundle", _raiser(RuntimeError("zip failed")))
    res = demos.get(f"/api/demos/{BID}/export")
    assert res.status_code == 400
    assert res.json()["detail"] == "zip failed"


def test_create_demo_capture_engine_failure_is_502(
    demos: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A CaptureFailedError from the engine surfaces as 502."""
    monkeypatch.setattr(PlaywrightCaptureEngine, "capture", _araiser(CaptureFailedError("nope")))
    res = demos.post(f"/api/demos/{BID}/captures", json={})
    assert res.status_code == 502
    assert res.json()["detail"] == "nope"


def test_capture_routes_engine_errors_map_to_404_and_400(
    demos: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Clear, delete and update capture map engine FileNotFound/ValueError to 404/400."""
    cases = (
        ("clear_all_captures", "delete", f"/api/demos/{BID}/captures", None),
        ("delete_capture", "delete", f"/api/demos/{BID}/captures/a.png", None),
        ("update_capture", "patch", f"/api/demos/{BID}/captures/a.png", {"label": "x"}),
    )
    for method, verb, url, body in cases:
        for exc, code in ((FileNotFoundError("nf"), 404), (ValueError("bad"), 400)):
            monkeypatch.setattr(PlaywrightCaptureEngine, method, _raiser(exc))
            res = demos.request(verb.upper(), url, json=body)
            assert res.status_code == code, (method, code)


def test_evaluate_and_pipeline_without_instance_are_400(demos: TestClient) -> None:
    """With no registered instance both endpoints ask for an active instance."""
    with db_session() as repo:
        repo.conn.execute("DELETE FROM instances;")
        repo.conn.commit()
    ev = demos.get(f"/api/demos/{BID}/evaluate")
    assert ev.status_code == 400
    assert "No active instance" in ev.json()["detail"]
    pipe = demos.post(f"/api/demos/{BID}/pipeline")
    assert pipe.status_code == 400


def test_evaluate_and_pipeline_engine_not_found_is_404(
    demos: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing bundle reported by the pipeline engine is a 404."""
    monkeypatch.setattr(DemoPipelineEngine, "evaluate_bundle", _raiser(FileNotFoundError("nf")))
    assert demos.get(f"/api/demos/{BID}/evaluate").status_code == 404
    monkeypatch.setattr(DemoPipelineEngine, "run_full_pipeline", _araiser(FileNotFoundError("x")))
    assert demos.post(f"/api/demos/{BID}/pipeline").status_code == 404


# --- sharing API (local mode and multi-user) --------------------------------------------

ADMIN, ANA, BEN = "admin@example.com", "ana@example.com", "ben@example.com"


@pytest.fixture
def team(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Admin owns the sample bundle; Ana and Ben are consultants."""
    bundles = tmp_path / "bundles"
    bundles.mkdir()
    shutil.copytree(SAMPLE, bundles / BID)
    monkeypatch.setenv("WORKBENCH_BUNDLES_DIR", str(bundles))
    with multi_user_client(ADMIN, (ANA, BEN)) as client:
        yield client


def _h(email: str) -> dict[str, str]:
    return as_user(email)


def test_groups_api_error_paths(team: TestClient) -> None:
    """Duplicate, missing, invalid and forbidden group operations are refused."""
    ok = team.post("/api/groups", json={"name": "EMEA", "kind": "region"}, headers=_h(ADMIN))
    gid = ok.json()["id"]
    dup = team.post("/api/groups", json={"name": "EMEA", "kind": "region"}, headers=_h(ADMIN))
    assert dup.status_code == 409
    assert team.delete("/api/groups/ghost", headers=_h(ADMIN)).status_code == 404
    assert team.post("/api/groups/ghost/join", headers=_h(ANA)).status_code == 404
    assert team.get(f"/api/groups/{gid}/members", headers=_h(ANA)).status_code == 403
    listed = team.get(f"/api/groups/{gid}/members", headers=_h(ADMIN))
    assert listed.status_code == 200
    bad = team.put(f"/api/groups/{gid}/members/not-an-email", json={}, headers=_h(ADMIN))
    assert bad.status_code == 422
    stranger = team.put(f"/api/groups/{gid}/members/who@example.com", json={}, headers=_h(ADMIN))
    assert stranger.status_code == 422
    assert "not on the Team" in stranger.json()["detail"]
    promote = team.put(f"/api/groups/{gid}/members/{BEN}", json={"role": "admin"}, headers=_h(ANA))
    assert promote.status_code == 403
    gone = team.delete(f"/api/groups/{gid}/members/{BEN}", headers=_h(ADMIN))
    assert gone.status_code == 404
    team.post(f"/api/groups/{gid}/join", headers=_h(ANA))
    assert team.delete(f"/api/groups/{gid}/members/{ANA}", headers=_h(ANA)).json() == {
        "removed": True
    }
    assert team.delete(f"/api/groups/{gid}", headers=_h(ADMIN)).json() == {"deleted": True}


def test_artifact_share_flow_errors_and_listings(team: TestClient) -> None:
    """Version/share listings are owner-only; sharing preconditions are enforced."""
    team.post(f"/api/demos/{BID}/clone", json={"target_bundle_id": "ana-copy"}, headers=_h(ADMIN))
    assert team.get(f"/api/artifacts/{BID}/versions", headers=_h(ANA)).status_code == 404
    assert team.get(f"/api/artifacts/{BID}/shares", headers=_h(ANA)).status_code == 404
    versions = team.get(f"/api/artifacts/{BID}/versions", headers=_h(ADMIN)).json()
    assert len(versions) >= 1
    assert team.get(f"/api/artifacts/{BID}/shares", headers=_h(ADMIN)).json() == []

    with db_session() as repo:
        repo.register_artifact("empty", ADMIN)
    unsaved = team.post("/api/artifacts/empty/shares", json={"target": "global"}, headers=_h(ADMIN))
    assert unsaved.status_code == 409

    no_group = team.post(
        f"/api/artifacts/{BID}/shares", json={"target": "group"}, headers=_h(ADMIN)
    )
    assert no_group.status_code == 422
    ghost = team.post(
        f"/api/artifacts/{BID}/shares",
        json={"target": "group", "group_id": "ghost"},
        headers=_h(ADMIN),
    )
    assert ghost.status_code == 404


def test_artifact_share_by_non_member_is_403_and_withdraw_and_decide_paths(
    team: TestClient,
) -> None:
    """Non-members cannot share to a group; withdraw and decide enforce ownership/rights."""
    gid = team.post(
        "/api/groups", json={"name": "APAC", "kind": "region"}, headers=_h(ADMIN)
    ).json()["id"]
    team.post(f"/api/artifacts/{BID}/shares", json={"target": "global"}, headers=_h(ADMIN))
    for who, name in ((ANA, "ana-demo"), (BEN, "ben-demo")):
        cloned = team.post(
            f"/api/demos/{BID}/clone", json={"target_bundle_id": name}, headers=_h(who)
        )
        assert cloned.status_code == 200
    team.put(f"/api/groups/{gid}/members/{ANA}", json={}, headers=_h(ADMIN))
    assert (
        team.post("/api/artifacts/ana-demo/versions", json={}, headers=_h(BEN)).status_code == 404
    )
    forbidden = team.post(
        "/api/artifacts/ben-demo/shares",
        json={"target": "group", "group_id": gid},
        headers=_h(BEN),
    )
    assert forbidden.status_code == 403

    share = team.post(
        "/api/artifacts/ana-demo/shares",
        json={"target": "group", "group_id": gid},
        headers=_h(ANA),
    ).json()
    assert share["status"] == "pending"
    assert (
        team.delete(f"/api/artifacts/ana-demo/shares/{share['id']}x", headers=_h(ANA)).status_code
        == 404
    )
    assert (
        team.post(
            "/api/approvals/shares/ghost", json={"approve": True}, headers=_h(ANA)
        ).status_code
        == 404
    )
    assert (
        team.post(
            f"/api/approvals/shares/{share['id']}", json={"approve": True}, headers=_h(BEN)
        ).status_code
        == 403
    )
    inbox = team.get("/api/approvals", headers=_h(ADMIN)).json()
    assert [s["id"] for s in inbox["shares"]] == [share["id"]]
    assert team.delete(f"/api/artifacts/ana-demo/shares/{share['id']}", headers=_h(ANA)).json() == {
        "withdrawn": True
    }
