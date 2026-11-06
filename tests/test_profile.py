# tests/test_profile.py
# Profile: servicenow.com email approval by one-time code, avatars, mail settings, migration.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for the profile feature (workflow, API, avatar safety, schema v5)."""

import re
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from now_workbench.api.app import create_app
from now_workbench.api.profile import mailer_factory
from now_workbench.db import db_session
from now_workbench.db.schema import MIGRATIONS, SCHEMA_VERSION, apply_migrations
from now_workbench.profile.avatars import MAX_AVATAR_BYTES, PRESET_AVATARS, sniff_image
from now_workbench.profile.mailer import InMemoryMailer, MailError, SmtpMailer
from now_workbench.profile.models import MailSettings, MailSettingsUpdate, ProfileUpdate
from now_workbench.profile.service import (
    CodeExpiredError,
    CooldownError,
    MailNotConfiguredError,
    NoEmailError,
    NoPendingCodeError,
    TooManyAttemptsError,
    WrongCodeError,
    confirm_code,
    send_code,
)
from now_workbench.profile.verification import (
    CODE_ALPHABET,
    CODE_LENGTH,
    code_matches,
    format_code,
    hash_code,
    new_code,
    normalize_code,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
NOW = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


def _code_from(mailer: InMemoryMailer) -> str:
    match = re.search(r"code is ([A-Z0-9]{4}-[A-Z0-9]{4})", mailer.sent[-1].body)
    assert match
    return match.group(1)


def _ready_repo(repo) -> None:
    repo.update_profile_identity("Pierre", "pierre@servicenow.com", NOW.isoformat())
    repo.put_mail_settings(MailSettingsUpdate(host="smtp.example.test", from_address="w@x.test"))


# --- verification helpers ---------------------------------------------------------------


def test_new_code_uses_the_unambiguous_alphabet_and_length() -> None:
    """Codes are 8 characters from the alphabet without 0, O, 1 and I."""
    for _ in range(50):
        code = new_code()
        assert len(code) == CODE_LENGTH
        assert set(code) <= set(CODE_ALPHABET)
    assert not set("01IO") & set(CODE_ALPHABET)


def test_code_matches_accepts_formatting_and_case() -> None:
    """The code as read from the email (dash, lower case, spaces) still matches."""
    code = new_code()
    stored = hash_code(code, "salt")
    assert code_matches(format_code(code).lower().replace("-", " - "), stored, "salt")
    assert not code_matches("WRONGCODE", stored, "salt")
    assert normalize_code(" ab-cd ") == "ABCD"


# --- models -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "email",
    ["a@gmail.com", "a@servicenow.com.evil.test", "a@sub.servicenow.com", "x@@servicenow.com"],
)
def test_profile_update_rejects_non_servicenow_addresses(email: str) -> None:
    """Only exact servicenow.com mailboxes are accepted."""
    with pytest.raises(ValueError, match="servicenow.com"):
        ProfileUpdate(email=email)


def test_profile_update_normalizes_servicenow_address() -> None:
    """Whitespace and case are normalized; empty is allowed."""
    assert (
        ProfileUpdate(email="  Pierre.Grothe@ServiceNow.com ").email
        == "pierre.grothe@servicenow.com"
    )
    assert ProfileUpdate(email="").email == ""


# --- workflow ---------------------------------------------------------------------------


def test_send_and_confirm_code_approves_the_profile(tmp_path: Path) -> None:
    """A code sent to the servicenow.com address approves the profile once."""
    mailer = InMemoryMailer()
    with db_session(tmp_path / "t.db") as repo:
        _ready_repo(repo)
        assert send_code(repo, mailer, NOW) == "pierre@servicenow.com"
        assert mailer.sent[0].to == "pierre@servicenow.com"
        confirm_code(repo, _code_from(mailer), NOW + timedelta(minutes=1))
        profile = repo.get_profile()
        assert profile.email_verified_at is not None
        assert profile.code_hash is None


def test_code_is_stored_hashed_never_in_clear(tmp_path: Path) -> None:
    """Only a salted hash of the code is persisted."""
    mailer = InMemoryMailer()
    with db_session(tmp_path / "t.db") as repo:
        _ready_repo(repo)
        send_code(repo, mailer, NOW)
        code = _code_from(mailer).replace("-", "")
        row = dict(repo.conn.execute("SELECT * FROM profile;").fetchone())
        assert code not in " ".join(str(v) for v in row.values())


def test_send_code_requires_a_servicenow_email(tmp_path: Path) -> None:
    """No saved servicenow.com address, no code."""
    with db_session(tmp_path / "t.db") as repo:
        repo.put_mail_settings(MailSettingsUpdate(host="h", from_address="f@x.test"))
        with pytest.raises(NoEmailError):
            send_code(repo, InMemoryMailer(), NOW)


def test_send_code_requires_mail_settings(tmp_path: Path) -> None:
    """Without SMTP settings nothing is pretended to be sent."""
    with db_session(tmp_path / "t.db") as repo:
        repo.update_profile_identity("P", "p@servicenow.com", NOW.isoformat())
        with pytest.raises(MailNotConfiguredError):
            send_code(repo, InMemoryMailer(), NOW)


def test_send_code_enforces_the_resend_cooldown(tmp_path: Path) -> None:
    """A second request within a minute is refused with the wait time."""
    with db_session(tmp_path / "t.db") as repo:
        _ready_repo(repo)
        mailer = InMemoryMailer()
        send_code(repo, mailer, NOW)
        with pytest.raises(CooldownError) as caught:
            send_code(repo, mailer, NOW + timedelta(seconds=10))
        assert caught.value.retry_after > 0
        send_code(repo, mailer, NOW + timedelta(seconds=61))
        assert len(mailer.sent) == 2


def test_failed_delivery_stores_no_code(tmp_path: Path) -> None:
    """If the email cannot be sent there is nothing to confirm."""
    with db_session(tmp_path / "t.db") as repo:
        _ready_repo(repo)
        with pytest.raises(MailError):
            send_code(repo, InMemoryMailer(fail_with="smtp down"), NOW)
        assert repo.get_profile().code_hash is None


def test_confirm_code_expires_after_ten_minutes(tmp_path: Path) -> None:
    """An old code is rejected and discarded."""
    mailer = InMemoryMailer()
    with db_session(tmp_path / "t.db") as repo:
        _ready_repo(repo)
        send_code(repo, mailer, NOW)
        with pytest.raises(CodeExpiredError):
            confirm_code(repo, _code_from(mailer), NOW + timedelta(minutes=11))
        assert repo.get_profile().code_hash is None


def test_confirm_code_locks_out_after_five_wrong_attempts(tmp_path: Path) -> None:
    """Guessing is capped; the code is discarded on the fifth miss."""
    mailer = InMemoryMailer()
    with db_session(tmp_path / "t.db") as repo:
        _ready_repo(repo)
        send_code(repo, mailer, NOW)
        for left in (4, 3, 2, 1):
            with pytest.raises(WrongCodeError) as caught:
                confirm_code(repo, "AAAAAAAA", NOW)
            assert caught.value.remaining == left
        with pytest.raises(TooManyAttemptsError):
            confirm_code(repo, "AAAAAAAA", NOW)
        with pytest.raises(NoPendingCodeError):
            confirm_code(repo, _code_from(mailer), NOW)


def test_changing_the_email_resets_approval(tmp_path: Path) -> None:
    """A different address is unverified and drops any pending code."""
    mailer = InMemoryMailer()
    with db_session(tmp_path / "t.db") as repo:
        _ready_repo(repo)
        send_code(repo, mailer, NOW)
        confirm_code(repo, _code_from(mailer), NOW)
        repo.update_profile_identity("P", "other@servicenow.com", NOW.isoformat())
        assert repo.get_profile().email_verified_at is None


# --- mailer -----------------------------------------------------------------------------


def test_smtp_mailer_reports_unreachable_server_as_mail_error() -> None:
    """A refused connection becomes a MailError, never a silent success."""
    mailer = SmtpMailer(MailSettings(host="127.0.0.1", port=1, from_address="a@b.test"), "")
    with pytest.raises(MailError):
        mailer.send("p@servicenow.com", "s", "b")


# --- avatars ----------------------------------------------------------------------------


def test_sniff_image_trusts_bytes_not_names() -> None:
    """PNG, JPEG and WebP are recognized; SVG and others are not."""
    assert sniff_image(PNG) == "image/png"
    assert sniff_image(b"\xff\xd8\xff\xe0abc") == "image/jpeg"
    assert sniff_image(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"
    assert sniff_image(b"<svg onload=alert(1)></svg>") is None
    assert sniff_image(b"GIF89a") is None


# --- API --------------------------------------------------------------------------------


@pytest.fixture
def mail() -> InMemoryMailer:
    """Shared in-memory mailer for API tests."""
    return InMemoryMailer()


@pytest.fixture
def client(mail: InMemoryMailer) -> TestClient:
    """Client over the real app with the in-memory mailer injected."""
    app = create_app()
    app.dependency_overrides[mailer_factory] = lambda: lambda _repo: mail
    return TestClient(app)


def test_profile_api_round_trip_and_servicenow_only(client: TestClient) -> None:
    """The profile saves; a non-servicenow address is a 422."""
    assert client.get("/api/profile").json()["email_verified"] is False
    ok = client.put("/api/profile", json={"display_name": "Pierre", "email": "p@servicenow.com"})
    assert ok.status_code == 200
    assert ok.json()["email"] == "p@servicenow.com"
    bad = client.put("/api/profile", json={"display_name": "P", "email": "p@gmail.com"})
    assert bad.status_code == 422


def test_verification_api_flow(client: TestClient, mail: InMemoryMailer) -> None:
    """Send then confirm over HTTP approves the profile; the hash is never exposed."""
    client.put("/api/profile", json={"display_name": "P", "email": "p@servicenow.com"})
    assert client.post("/api/profile/verification/send").status_code == 409  # no SMTP yet
    client.put("/api/profile/mail", json={"host": "smtp.test", "from_address": "w@x.test"})
    sent = client.post("/api/profile/verification/send")
    assert sent.status_code == 200
    assert sent.json()["sent_to"] == "p@servicenow.com"
    assert client.post("/api/profile/verification/send").status_code == 429
    wrong = client.post("/api/profile/verification/confirm", json={"code": "AAAAAAAA"})
    assert wrong.status_code == 400
    done = client.post("/api/profile/verification/confirm", json={"code": _code_from(mail)})
    assert done.status_code == 200
    assert done.json()["email_verified"] is True
    assert "code_hash" not in done.text


def test_confirm_without_a_code_is_conflict(client: TestClient) -> None:
    """Confirming when nothing was requested is a 409."""
    res = client.post("/api/profile/verification/confirm", json={"code": "ABCD-EFGH"})
    assert res.status_code == 409


def test_failed_delivery_is_bad_gateway(client: TestClient, mail: InMemoryMailer) -> None:
    """A delivery failure is reported, not hidden."""
    mail.fail_with = "relay denied"
    client.put("/api/profile", json={"display_name": "P", "email": "p@servicenow.com"})
    client.put("/api/profile/mail", json={"host": "smtp.test", "from_address": "w@x.test"})
    res = client.post("/api/profile/verification/send")
    assert res.status_code == 502
    assert "relay denied" in res.json()["detail"]


def test_mail_settings_never_return_the_password(client: TestClient) -> None:
    """The SMTP password is sealed; the API only says whether one is set."""
    client.put(
        "/api/profile/mail",
        json={"host": "h", "from_address": "f@x.test", "username": "u", "password": "s3cret-pw"},
    )
    got = client.get("/api/profile/mail")
    assert got.json()["has_password"] is True
    assert "s3cret-pw" not in got.text
    keep = client.put("/api/profile/mail", json={"host": "h2", "from_address": "f@x.test"})
    assert keep.json()["has_password"] is True
    cleared = client.put(
        "/api/profile/mail", json={"host": "h2", "from_address": "f@x.test", "password": ""}
    )
    assert cleared.json()["has_password"] is False


def test_preset_avatar_choice(client: TestClient) -> None:
    """A built-in avatar can be chosen; unknown ids are refused."""
    ok = client.put("/api/profile/avatar/preset", json={"preset": PRESET_AVATARS[0]})
    assert ok.json()["avatar"] == {"kind": "preset", "preset": PRESET_AVATARS[0], "url": None}
    assert client.put("/api/profile/avatar/preset", json={"preset": "nope"}).status_code == 422


def test_avatar_upload_serve_and_remove(client: TestClient) -> None:
    """A PNG upload is stored, served with nosniff, and removable."""
    up = client.put("/api/profile/avatar", content=PNG, headers={"content-type": "image/png"})
    assert up.status_code == 200
    assert up.json()["avatar"]["kind"] == "upload"
    got = client.get("/api/profile/avatar")
    assert got.status_code == 200
    assert got.headers["content-type"] == "image/png"
    assert got.headers["x-content-type-options"] == "nosniff"
    assert got.content == PNG
    client.delete("/api/profile/avatar")
    assert client.get("/api/profile/avatar").status_code == 404


def test_avatar_upload_rejects_svg_and_oversize(client: TestClient) -> None:
    """Only real PNG/JPEG/WebP bytes up to 2 MB are accepted."""
    svg = client.put(
        "/api/profile/avatar", content=b"<svg/>", headers={"content-type": "image/png"}
    )
    assert svg.status_code == 415
    big = client.put("/api/profile/avatar", content=PNG + b"\x00" * MAX_AVATAR_BYTES)
    assert big.status_code == 413


# --- migration --------------------------------------------------------------------------


def test_apply_migrations_v4_to_v5_creates_profile_tables() -> None:
    """Upgrading adds the profile and mail_settings tables and keeps existing data."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "BEGIN;\n" + "\n".join(MIGRATIONS[:4]) + "\nPRAGMA user_version = 4;\nCOMMIT;"
    )
    assert apply_migrations(conn) == SCHEMA_VERSION == 5
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';")}
    assert {"profile", "mail_settings"} <= tables
    conn.close()


def test_preset_avatar_ids_match_the_web_ui() -> None:
    """The built-in avatar ids in Python and TypeScript are the same, in order."""
    source = (Path(__file__).resolve().parent.parent / "web/src/profile/avatars.ts").read_text()
    web_ids = re.findall(r"\{ id: '([a-z]+)', bg:", source)
    assert tuple(web_ids) == PRESET_AVATARS
