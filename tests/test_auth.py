# tests/test_auth.py
# Cloudflare Access sign-in, role mapping, role-gated routes and the fail-closed startup guard.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for now_workbench.auth (ADR-016)."""

import base64
import hashlib
import hmac
import json
import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from now_workbench.domains.identity.models import Role
from now_workbench.domains.identity.repository import UserRepository
from now_workbench.interfaces.api.access import ACCESS_HEADER, AccessValidator
from now_workbench.interfaces.api.app import create_app
from now_workbench.interfaces.api.guard import assert_safe_binding, is_loopback_host
from now_workbench.platform.db.session import db_session

TEAM = "example.cloudflareaccess.com"
AUD = "aud-tag-123"
ADMIN = "pierre@example.com"
SC = "consultant@example.com"
OUTSIDER = "stranger@example.com"

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _token(
    email: str | None = ADMIN,
    *,
    aud: str = AUD,
    iss: str = f"https://{TEAM}",
    exp_in: int = 600,
    key: Any = _KEY,
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {"aud": aud, "iss": iss, "iat": now, "exp": now + exp_in}
    if email is not None:
        claims["email"] = email
    return jwt.encode(claims, key, algorithm="RS256")


def _validator() -> AccessValidator:
    return AccessValidator(TEAM, AUD, key_resolver=lambda _token: _KEY.public_key())


@pytest.fixture
def signed_in() -> TestClient:
    """App with Access configured; ADMIN holds both roles, SC is a consultant only."""
    with db_session() as conn:
        user_repo = UserRepository(conn)
        user_repo.put_user(ADMIN, frozenset(Role), added_by="test")
        user_repo.put_user(SC, frozenset({Role.SOLUTION_CONSULTANT}), added_by="test")
    return TestClient(
        create_app(access_validator=_validator(), announce_setup_code=lambda _c: None)
    )


def _as(email: str | None, **kwargs: Any) -> dict[str, str]:
    return {ACCESS_HEADER: _token(email, **kwargs)}


# --- token validation -------------------------------------------------------------------


def test_valid_token_yields_the_normalized_email() -> None:
    """A correctly signed token for this application returns its lower-cased email."""
    assert _validator().email(_token("Pierre@Example.com")) == "pierre@example.com"


@pytest.mark.parametrize(
    "token",
    [
        _token(aud="another-app"),
        _token(iss="https://evil.cloudflareaccess.com"),
        _token(exp_in=-10),
        _token(key=_OTHER_KEY),
        _token(email=None),
        "not-a-jwt",
        "",
    ],
)
def test_bad_tokens_are_refused(token: str) -> None:
    """Wrong audience, issuer, expiry, signer, no email, or garbage all yield no identity."""
    assert _validator().email(token) is None


def test_symmetric_algorithm_confusion_is_refused() -> None:
    """A token HMAC-signed with the public key (hand-built; PyJWT refuses to) is rejected."""
    public_pem = _KEY.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )

    def b64(raw: bytes) -> bytes:
        return base64.urlsafe_b64encode(raw).rstrip(b"=")

    now = int(time.time())
    header = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    claims = b64(
        json.dumps(
            {"aud": AUD, "iss": f"https://{TEAM}", "iat": now, "exp": now + 60, "email": ADMIN}
        ).encode()
    )
    signing_input = header + b"." + claims
    signature = b64(hmac.new(public_pem, signing_input, hashlib.sha256).digest())
    forged = (signing_input + b"." + signature).decode()
    assert _validator().email(forged) is None


# --- requests ---------------------------------------------------------------------------


def test_request_without_a_token_is_forbidden_when_access_is_configured(
    signed_in: TestClient,
) -> None:
    """With Access configured there is no anonymous route in."""
    assert signed_in.get("/api/profile").status_code == 403
    assert signed_in.get("/api/instances").status_code == 403


def test_user_with_no_role_is_forbidden(signed_in: TestClient) -> None:
    """A valid Cloudflare identity that is on neither list gets nothing."""
    res = signed_in.get("/api/profile", headers=_as(OUTSIDER))
    assert res.status_code == 403
    assert OUTSIDER in res.json()["detail"]


def test_owner_has_both_roles(signed_in: TestClient) -> None:
    """The admin address configured on both lists reports both roles."""
    body = signed_in.get("/api/profile", headers=_as(ADMIN)).json()
    assert body["email"] == ADMIN
    assert body["roles"] == ["admin", "solution_consultant"]
    assert body["auth_mode"] == "cloudflare"


def test_register_instance_is_private_to_its_owner(signed_in: TestClient) -> None:
    """A consultant registers their own instance; the admin neither sees nor deletes it."""
    payload = {"name": "Mine", "url": "fake://x.service-now.com", "username": "u", "password": "p"}
    created = signed_in.post("/api/instances", json=payload, headers=_as(SC))
    assert created.status_code == 200
    inst_id = created.json()["id"]
    admin_view = signed_in.get("/api/instances", headers=_as(ADMIN)).json()
    assert inst_id not in {i["id"] for i in admin_view}
    assert signed_in.delete(f"/api/instances/{inst_id}", headers=_as(ADMIN)).status_code == 404
    assert signed_in.delete(f"/api/instances/{inst_id}", headers=_as(SC)).status_code == 200


def test_admin_can_register_an_instance(signed_in: TestClient) -> None:
    """The same call succeeds for an admin."""
    payload = {"name": "Auth Test", "url": "fake://auth.service-now.com", "password": "p"}
    assert signed_in.post("/api/instances", json=payload, headers=_as(ADMIN)).status_code == 200


def test_claude_key_changes_need_admin_but_other_settings_do_not(signed_in: TestClient) -> None:
    """Consultants may tune non-secret preferences, not touch the API key."""
    headers = _as(SC)
    ok = signed_in.put("/api/settings", json={"narrative_tone": "executive"}, headers=headers)
    assert ok.status_code == 200
    key = signed_in.put("/api/settings", json={"anthropic_api_key": "sk-ant-x"}, headers=headers)
    assert key.status_code == 403
    assert signed_in.delete("/api/settings/api-key", headers=headers).status_code == 403
    # Settings are per user (ADR-018): resetting your own never touches the shared key.
    assert signed_in.post("/api/settings/reset", headers=headers).status_code == 200


def test_identity_cannot_be_forged_through_the_body(signed_in: TestClient) -> None:
    """The profile belongs to the verified email; the body cannot name another user."""
    res = signed_in.put("/api/profile", json={"display_name": "A", "email": ADMIN}, headers=_as(SC))
    assert res.status_code == 422


def test_websocket_without_a_token_is_closed(signed_in: TestClient) -> None:
    """The log stream is not reachable anonymously."""
    with pytest.raises(WebSocketDisconnect), signed_in.websocket_connect("/ws/logs"):
        pass


# --- local mode and the startup guard ----------------------------------------------------


def test_local_mode_is_a_single_user_with_both_roles() -> None:
    """With Access unconfigured on loopback the app works as before, as the local user."""
    client = TestClient(create_app(access_validator=AccessValidator("", "")))
    body = client.get("/api/profile").json()
    assert body["auth_mode"] == "local"
    assert body["roles"] == ["admin", "solution_consultant"]


@pytest.mark.parametrize(
    "header",
    ["cf-ray", "cf-connecting-ip", ACCESS_HEADER, "x-forwarded-for", "forwarded", "x-real-ip"],
)
def test_cloudflare_traffic_is_refused_when_access_is_not_configured(header: str) -> None:
    """A tunnel in front of an unconfigured server must not silently open it."""
    client = TestClient(create_app(access_validator=AccessValidator("", "")))
    assert client.get("/api/profile", headers={header: "x"}).status_code == 403


@pytest.mark.parametrize(
    ("host", "expected"), [("127.0.0.1", True), ("::1", True), ("0.0.0.0", False)]
)
def test_is_loopback_host(host: str, expected: bool) -> None:
    """Only loopback names count as local."""
    assert is_loopback_host(host) is expected


def test_assert_safe_binding_fails_closed() -> None:
    """Listening beyond loopback needs Access; loopback or configured Access is fine."""
    unconfigured = AccessValidator("", "")
    with pytest.raises(RuntimeError, match="Refusing to listen"):
        assert_safe_binding("0.0.0.0", unconfigured)
    assert_safe_binding("127.0.0.1", unconfigured)
    assert_safe_binding("0.0.0.0", _validator())


def test_serve_refuses_a_public_bind_without_access() -> None:
    """`workbench serve --host 0.0.0.0` exits before listening when Access is not configured."""
    from typer.testing import CliRunner

    from now_workbench.interfaces.cli.main import app as cli_app

    result = CliRunner().invoke(cli_app, ["serve", "--host", "0.0.0.0", "--port", "8099"])
    assert result.exit_code == 1
    assert "Refusing to listen" in result.stdout
