# tests/test_profile.py
# Per-user profile: display name, built-in avatars, picture upload safety, schema v5.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for the profile feature (ADR-016)."""

import re
import sqlite3
import time
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from now_workbench.api.app import create_app
from now_workbench.auth.access import ACCESS_HEADER, AccessValidator
from now_workbench.db.schema import MIGRATIONS, SCHEMA_VERSION, apply_migrations
from now_workbench.profile.avatars import MAX_AVATAR_BYTES, PRESET_AVATARS, sniff_image

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _as(email: str) -> dict[str, str]:
    now = int(time.time())
    token = jwt.encode(
        {
            "aud": "a",
            "iss": "https://t.cloudflareaccess.com",
            "iat": now,
            "exp": now + 600,
            "email": email,
        },
        _KEY,
        algorithm="RS256",
    )
    return {ACCESS_HEADER: token}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """App with Access configured and two consultants."""
    monkeypatch.setenv("WORKBENCH_CONSULTANT_EMAILS", "a@example.com b@example.com")
    validator = AccessValidator(
        "t.cloudflareaccess.com", "a", key_resolver=lambda _t: _KEY.public_key()
    )
    return TestClient(create_app(access_validator=validator))


def test_sniff_image_trusts_bytes_not_names() -> None:
    """PNG, JPEG and WebP are recognized; SVG and others are not."""
    assert sniff_image(PNG) == "image/png"
    assert sniff_image(b"\xff\xd8\xff\xe0abc") == "image/jpeg"
    assert sniff_image(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"
    assert sniff_image(b"<svg onload=alert(1)></svg>") is None
    assert sniff_image(b"GIF89a") is None


def test_display_name_is_saved_per_user(client: TestClient) -> None:
    """Each signed-in email has its own profile."""
    client.put("/api/profile", json={"display_name": "  Ann  "}, headers=_as("a@example.com"))
    assert client.get("/api/profile", headers=_as("a@example.com")).json()["display_name"] == "Ann"
    assert client.get("/api/profile", headers=_as("b@example.com")).json()["display_name"] == ""


def test_preset_avatar_choice(client: TestClient) -> None:
    """A built-in avatar can be chosen; unknown ids are refused."""
    h = _as("a@example.com")
    ok = client.put("/api/profile/avatar/preset", json={"preset": PRESET_AVATARS[0]}, headers=h)
    assert ok.json()["avatar"] == {"kind": "preset", "preset": PRESET_AVATARS[0], "url": None}
    assert (
        client.put("/api/profile/avatar/preset", json={"preset": "nope"}, headers=h).status_code
        == 422
    )


def test_avatar_upload_is_private_to_the_user(client: TestClient) -> None:
    """A PNG upload is served with nosniff to its owner only, and removable."""
    mine, theirs = _as("a@example.com"), _as("b@example.com")
    up = client.put(
        "/api/profile/avatar", content=PNG, headers={**mine, "content-type": "image/png"}
    )
    assert up.status_code == 200
    assert up.json()["avatar"]["kind"] == "upload"
    got = client.get("/api/profile/avatar", headers=mine)
    assert got.headers["content-type"] == "image/png"
    assert got.headers["x-content-type-options"] == "nosniff"
    assert got.content == PNG
    assert client.get("/api/profile/avatar", headers=theirs).status_code == 404
    client.delete("/api/profile/avatar", headers=mine)
    assert client.get("/api/profile/avatar", headers=mine).status_code == 404


def test_avatar_upload_rejects_svg_and_oversize(client: TestClient) -> None:
    """Only real PNG/JPEG/WebP bytes up to 2 MB are accepted."""
    h = _as("a@example.com")
    svg = client.put(
        "/api/profile/avatar", content=b"<svg/>", headers={**h, "content-type": "image/png"}
    )
    assert svg.status_code == 415
    big = client.put("/api/profile/avatar", content=PNG + b"\x00" * MAX_AVATAR_BYTES, headers=h)
    assert big.status_code == 413


def test_preset_avatar_ids_match_the_web_ui() -> None:
    """The built-in avatar ids in Python and TypeScript are the same, in order."""
    source = (Path(__file__).resolve().parent.parent / "web/src/profile/avatars.ts").read_text()
    assert tuple(re.findall(r"\{ id: '([a-z]+)', bg:", source)) == PRESET_AVATARS


def test_apply_migrations_v4_to_v5_creates_the_profile_table() -> None:
    """Upgrading adds the per-user profile table."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    script = "\n".join(MIGRATIONS[:4])
    conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = 4;\nCOMMIT;")
    assert apply_migrations(conn) == SCHEMA_VERSION == 5
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(profile);")}
    assert {"email", "display_name", "avatar_kind"} <= cols
    conn.close()
