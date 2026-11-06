# tests/test_setup_and_team.py
# First-run setup code, the Team (roles) API, the health probe and the backup command.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for ADR-017: first administrator by setup code, team management, operations."""

import re
import sqlite3
import time
from pathlib import Path
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from now_workbench.api.app import create_app
from now_workbench.auth.access import ACCESS_HEADER, AccessValidator
from now_workbench.auth.models import Role
from now_workbench.auth.setup import MAX_ATTEMPTS, SetupCodes, TooManyAttemptsError, WrongCodeError
from now_workbench.cli import app as cli_app
from now_workbench.db import db_session

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
TEAM, AUD = "t.cloudflareaccess.com", "aud"
OWNER, OTHER = "owner@example.com", "other@example.com"


def _as(email: str) -> dict[str, str]:
    now = int(time.time())
    claims: dict[str, Any] = {
        "aud": AUD,
        "iss": f"https://{TEAM}",
        "iat": now,
        "exp": now + 600,
        "email": email,
    }
    return {ACCESS_HEADER: jwt.encode(claims, _KEY, algorithm="RS256")}


@pytest.fixture
def codes() -> list[str]:
    """Setup codes the app announces (instead of the server log)."""
    return []


@pytest.fixture
def client(codes: list[str]) -> TestClient:
    """A fresh Access-protected app with no administrator yet; startup issues the code."""
    validator = AccessValidator(TEAM, AUD, key_resolver=lambda _t: _KEY.public_key())
    app = create_app(access_validator=validator, announce_setup_code=codes.append)
    with TestClient(app) as test_client:
        yield test_client


# --- setup codes ------------------------------------------------------------------------


def test_setup_code_is_announced_once_and_accepted_once() -> None:
    """A code works one time, regardless of case and dash."""
    seen: list[str] = []
    holder = SetupCodes(seen.append)
    holder.issue()
    assert re.fullmatch(r"[A-Z2-9]{4}-[A-Z2-9]{4}", seen[0])
    holder.redeem(seen[0].lower().replace("-", " "))
    assert not holder.active


def test_setup_code_is_replaced_after_too_many_misses() -> None:
    """Five wrong tries retire the code and announce a new one."""
    seen: list[str] = []
    holder = SetupCodes(seen.append)
    holder.issue()
    for _ in range(MAX_ATTEMPTS - 1):
        with pytest.raises(WrongCodeError):
            holder.redeem("AAAA-AAAA")
    with pytest.raises(TooManyAttemptsError):
        holder.redeem("AAAA-AAAA")
    assert len(seen) == 2
    with pytest.raises(WrongCodeError):
        holder.redeem(seen[0])
    holder.redeem(seen[1])


# --- first run ----------------------------------------------------------------------------


def test_startup_issues_a_code_when_no_admin_exists(client: TestClient, codes: list[str]) -> None:
    """The first start of an Access-protected server writes one code to the log."""
    assert len(codes) == 1


def test_roleless_user_sees_only_the_ui_and_setup(client: TestClient) -> None:
    """Before setup, a signed-in person can load the UI and the setup API, nothing else."""
    status = client.get("/api/setup/status", headers=_as(OWNER)).json()
    assert status == {
        "setup_required": True,
        "email": OWNER,
        "has_role": False,
        "auth_mode": "cloudflare",
    }
    blocked = client.get("/api/instances", headers=_as(OWNER))
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "setup_required"


def test_entering_the_code_makes_the_first_admin(client: TestClient, codes: list[str]) -> None:
    """The right code gives both roles to the signed-in email and closes setup."""
    wrong = client.post("/api/setup", json={"code": "AAAA-AAAA"}, headers=_as(OWNER))
    assert wrong.status_code == 400
    done = client.post("/api/setup", json={"code": codes[0]}, headers=_as(OWNER))
    assert done.status_code == 200
    with db_session() as repo:
        assert repo.get_user_roles(OWNER) == frozenset(Role)
    again = client.post("/api/setup", json={"code": codes[0]}, headers=_as(OTHER))
    assert again.status_code == 409
    other = client.get("/api/instances", headers=_as(OTHER))
    assert other.json()["code"] == "no_role"


def test_setup_needs_a_cloudflare_identity(client: TestClient) -> None:
    """Without a signed token nothing is reachable, not even setup."""
    assert client.get("/api/setup/status").status_code == 403
    assert client.post("/api/setup", json={"code": "AAAA-AAAA"}).status_code == 403


# --- team -------------------------------------------------------------------------------


def _owner_admin() -> None:
    with db_session() as repo:
        repo.put_user(OWNER, frozenset(Role), added_by="test")


def test_admin_adds_changes_and_removes_members(client: TestClient) -> None:
    """Admins manage who is allowed in and with which roles."""
    _owner_admin()
    h = _as(OWNER)
    added = client.put(f"/api/team/{OTHER}", json={"solution_consultant": True}, headers=h)
    assert {"email": OTHER, "roles": ["solution_consultant"]}.items() <= next(
        m for m in added.json() if m["email"] == OTHER
    ).items()
    assert client.get("/api/profile", headers=_as(OTHER)).status_code == 200
    assert client.get("/api/team", headers=_as(OTHER)).status_code == 403
    assert client.delete(f"/api/team/{OTHER}", headers=h).status_code == 200
    assert client.get("/api/profile", headers=_as(OTHER)).status_code == 403


def test_team_keeps_at_least_one_admin(client: TestClient) -> None:
    """The last administrator cannot be removed or demoted."""
    _owner_admin()
    h = _as(OWNER)
    assert client.delete(f"/api/team/{OWNER}", headers=h).status_code == 409
    demote = client.put(f"/api/team/{OWNER}", json={"solution_consultant": True}, headers=h)
    assert demote.status_code == 409
    assert client.put(f"/api/team/{OTHER}", json={}, headers=h).status_code == 422
    assert client.put("/api/team/not-an-email", json={"admin": True}, headers=h).status_code == 422


# --- operations ---------------------------------------------------------------------------


def test_healthz_answers_without_sign_in_and_reveals_nothing(client: TestClient) -> None:
    """The container health probe works without a token and only says ok."""
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
    assert client.get("/api/health").status_code == 403


def test_backup_writes_a_consistent_database_copy(tmp_path: Path) -> None:
    """`workbench backup -o file` produces a readable SQLite copy."""
    with db_session() as repo:
        repo.put_user(OWNER, frozenset(Role), added_by="test")
    out = tmp_path / "backup.db"
    result = CliRunner().invoke(cli_app, ["backup", "--out", str(out)])
    assert result.exit_code == 0, result.stdout
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT email FROM users;").fetchone()[0] == OWNER
    conn.close()
