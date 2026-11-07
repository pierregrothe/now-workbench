# tests/test_retention_and_s3.py
# Telemetry retention and backups to an S3-compatible bucket (ADR-029).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests for the telemetry purge, its server loop, SigV4 signing and `backup --s3`."""

import asyncio
import hashlib
import logging
import re
import sqlite3
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from typer.testing import CliRunner

from now_workbench.domains.telemetry import purge_expired
from now_workbench.interfaces.api import retention
from now_workbench.interfaces.api.app import create_app
from now_workbench.interfaces.cli import main as cli_mod
from now_workbench.platform import s3
from now_workbench.platform.config.settings import Settings, settings
from now_workbench.platform.db.session import db_session
from now_workbench.platform.s3 import S3Target, put_object, sign_v4

NOW = datetime(2026, 11, 7, 12, 0, 0, tzinfo=UTC)
# 30 days before NOW is the cutoff: one event a millisecond older, one exactly at it.
OLD = "2026-10-08T11:59:59.999Z"
EDGE = "2026-10-08T12:00:00.000Z"
EMPTY = (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"  # SHA-256 of an empty body
)
TARGET = S3Target(
    bucket="wb-backups",
    region="ca-central-1",
    access_key_id="AKIDEXAMPLE",
    secret_access_key="wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY",
)


def _seed(stamps: list[tuple[str, str]]) -> None:
    """Insert one usage and one action event per (owner, created_at)."""
    with db_session() as conn, conn:
        for owner, at in stamps:
            conn.execute(
                "INSERT INTO usage_events (owner_email, actor_email, model, input_tokens, "
                "output_tokens, cache_write, cache_read, created_at) "
                "VALUES (?, ?, 'm', 1, 1, 0, 0, ?);",
                (owner, owner, at),
            )
            conn.execute(
                "INSERT INTO action_events (owner_email, actor_email, name, source, outcome, "
                "duration_ms, created_at) VALUES (?, ?, 'a', 'otto', 'ok', 1, ?);",
                (owner, owner, at),
            )


def _left() -> list[tuple[str, str, str]]:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT 'usage', owner_email, created_at FROM usage_events UNION ALL "
            "SELECT 'action', owner_email, created_at FROM action_events ORDER BY 1, 2, 3;"
        ).fetchall()
    return [tuple(r) for r in rows]


# --------------------------------------------------------------------------- retention


def test_purge_expired_deletes_everyone_before_the_cutoff_and_keeps_the_edge() -> None:
    _seed([("a@x.com", OLD), ("b@x.com", OLD), ("a@x.com", EDGE)])
    with db_session() as conn:
        assert purge_expired(conn, 30, NOW) == 4
    assert _left() == [("action", "a@x.com", EDGE), ("usage", "a@x.com", EDGE)]


def test_purge_expired_with_nothing_old_deletes_nothing() -> None:
    _seed([("a@x.com", EDGE)])
    with db_session() as conn:
        assert purge_expired(conn, 30, NOW) == 0
    assert len(_left()) == 2


def test_purge_telemetry_uses_the_configured_retention(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(settings, "telemetry_retention_days", 60)
    _seed([("a@x.com", "2001-01-01T00:00:00.000Z"), ("a@x.com", "2999-01-01T00:00:00.000Z")])
    with caplog.at_level(logging.INFO, logger=retention.__name__):
        assert retention.purge_telemetry() == 2
    assert caplog.messages == ["Telemetry purge: 2 events older than 60 days deleted."]
    caplog.clear()
    with caplog.at_level(logging.INFO, logger=retention.__name__):
        assert retention.purge_telemetry() == 0
    assert caplog.messages == []


def test_purge_telemetry_logs_a_database_error_and_keeps_running(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def broken(*_: Any) -> int:
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(retention, "purge_expired", broken)
    assert retention.purge_telemetry() == 0
    assert [r.levelno for r in caplog.records] == [logging.ERROR]
    assert caplog.messages == ["Telemetry purge failed; events are kept until the next run."]


async def test_telemetry_retention_purges_at_start_and_on_every_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs: list[int] = []
    monkeypatch.setattr(retention, "purge_telemetry", lambda: runs.append(1) or 0)
    async with asyncio.timeout(2), retention.telemetry_retention(interval=0.01):
        while len(runs) < 3:
            await asyncio.sleep(0.005)
    done = len(runs)
    await asyncio.sleep(0.05)
    assert len(runs) == done


async def test_telemetry_retention_defaults_to_one_purge_a_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs: list[int] = []
    monkeypatch.setattr(retention, "purge_telemetry", lambda: runs.append(1) or 0)
    async with retention.telemetry_retention():
        await asyncio.sleep(0.05)
    assert runs == [1]


def test_create_app_startup_purges_expired_telemetry() -> None:
    _seed([("a@x.com", "2001-01-01T00:00:00.000Z")])
    with TestClient(create_app()):
        pass
    assert _left() == []


def test_settings_retention_shorter_than_the_longest_chart_is_refused() -> None:
    assert Settings().telemetry_retention_days == 365
    assert Settings(telemetry_retention_days=60).telemetry_retention_days == 60
    with pytest.raises(ValidationError):
        Settings(telemetry_retention_days=59)


# --------------------------------------------------------------------------- SigV4 and upload


def test_sign_v4_matches_the_botocore_reference_signature() -> None:
    """Vector produced by botocore's S3SigV4Auth for the same request (2026-11-07)."""
    body = b"SQLite format 3\x00test"
    payload = hashlib.sha256(body).hexdigest()
    assert payload == "18e851abfac892230fd8d830d2e5e201d3aea8341a874a675eea2182a86830a4"
    auth = sign_v4(
        TARGET,
        "PUT",
        "https://s3.ca-central-1.amazonaws.com/wb-backups/now-workbench/"
        "workbench-20261107T020000Z.db",
        {
            "Host": "s3.ca-central-1.amazonaws.com",
            "x-amz-content-sha256": payload,
            "X-Amz-Date": "20261107T092331Z",
            "content-type": "application/octet-stream",
        },
        payload,
    )
    assert auth == (
        "AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20261107/ca-central-1/s3/aws4_request, "
        "SignedHeaders=content-type;host;x-amz-content-sha256;x-amz-date, "
        "Signature=8290f2712ec55a70a03b38a5375c392c7d501d23697a875ef9e1b9196d205e82"
    )


def test_sign_v4_folds_header_whitespace_and_signs_the_root_path() -> None:
    """Second botocore vector: a bare-host URL and a header with runs of spaces."""
    headers = {
        "host": "s3.ca-central-1.amazonaws.com",
        "x-amz-content-sha256": EMPTY,
        "x-amz-date": "20261107T092749Z",
        "x-amz-meta-note": "  a   b  c ",
    }
    auth = sign_v4(TARGET, "GET", "https://s3.ca-central-1.amazonaws.com", headers, EMPTY)
    assert auth == (
        "AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20261107/ca-central-1/s3/aws4_request, "
        "SignedHeaders=host;x-amz-content-sha256;x-amz-date;x-amz-meta-note, "
        "Signature=8bf4056258b34ad5bcb997e140b4c0a3965c02a7230ca7265eaea41ad7bb8ad1"
    )


def _capture(status: int = 200, text: str = "") -> tuple[list[httpx.Request], httpx.MockTransport]:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status, text=text)

    return seen, httpx.MockTransport(handle)


def test_put_object_sends_a_signed_put_of_the_body() -> None:
    seen, transport = _capture()
    where = put_object(TARGET, "now-workbench/a b.db", b"data", now=NOW, transport=transport)
    assert where == "s3://wb-backups/now-workbench/a b.db"
    (req,) = seen
    assert req.method == "PUT"
    assert str(req.url) == "https://s3.ca-central-1.amazonaws.com/wb-backups/now-workbench/a%20b.db"
    assert req.content == b"data"
    digest = hashlib.sha256(b"data").hexdigest()
    sent = {
        k: req.headers[k] for k in ("host", "x-amz-content-sha256", "x-amz-date", "content-type")
    }
    assert sent == {
        "host": "s3.ca-central-1.amazonaws.com",
        "x-amz-content-sha256": digest,
        "x-amz-date": "20261107T120000Z",
        "content-type": "application/octet-stream",
    }
    assert req.headers["authorization"] == sign_v4(TARGET, "PUT", str(req.url), sent, digest)


def test_put_object_uses_a_custom_endpoint_path_style() -> None:
    seen, transport = _capture()
    r2 = S3Target("bkt", "auto", "k", "s", endpoint="https://acct.r2.cloudflarestorage.com/")
    put_object(r2, "x.db", b"", transport=transport)
    assert str(seen[0].url) == "https://acct.r2.cloudflarestorage.com/bkt/x.db"
    assert S3Target("b", "r", "k", "s", endpoint="https://storeX/").base_url() == "https://storeX"
    assert re.fullmatch(r"\d{8}T\d{6}Z", seen[0].headers["x-amz-date"])


def test_put_object_reports_a_refusal_with_its_status() -> None:
    _, transport = _capture(403, "<Error><Code>AccessDenied</Code></Error>" + "x" * 400)
    with pytest.raises(RuntimeError) as err:
        put_object(TARGET, "k", b"", now=NOW, transport=transport)
    assert str(err.value) == (
        "S3 refused the upload (403): <Error><Code>AccessDenied</Code></Error>" + "x" * 260
    )


def test_put_object_refuses_a_plain_http_endpoint() -> None:
    seen, transport = _capture()
    plain = S3Target("b", "r", "k", "s", endpoint="http://minio.local:9000")
    with pytest.raises(ValueError, match=r"^S3 endpoint must use https: http://minio.local:9000$"):
        put_object(plain, "k", b"", transport=transport)
    assert seen == []


def test_put_object_waits_up_to_a_minute() -> None:
    seen, transport = _capture()
    put_object(TARGET, "k", b"", now=NOW, transport=transport)
    assert seen[0].extensions["timeout"] == httpx.Timeout(60.0).as_dict()


@pytest.mark.parametrize("name", ["ab", "Bad_Bucket", "ok-bucket/../other", "-lead", "trail."])
def test_put_object_refuses_an_invalid_bucket_name(name: str) -> None:
    seen, transport = _capture()
    bad = S3Target(name, "r", "k", "s")
    with pytest.raises(ValueError) as err:
        put_object(bad, "k", b"", transport=transport)
    assert str(err.value) == f"Not a valid S3 bucket name: {name!r}"
    assert seen == []


def test_put_object_signs_with_the_current_utc_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(s3, "utc_now", lambda: NOW)
    seen, transport = _capture()
    put_object(S3Target("abc", "r", "k", "s"), "k", b"", transport=transport)
    assert seen[0].headers["x-amz-date"] == "20261107T120000Z"


# --------------------------------------------------------------------------- backup --s3


@pytest.fixture
def bucket(monkeypatch: pytest.MonkeyPatch) -> list[tuple[S3Target, str, bytes]]:
    sent: list[tuple[S3Target, str, bytes]] = []

    def fake_put(target: S3Target, key: str, body: bytes) -> str:
        sent.append((target, key, body))
        return f"s3://{target.bucket}/{key}"

    for name, value in {
        "backup_s3_bucket": "wb-backups",
        "backup_s3_region": "ca-central-1",
        "backup_s3_endpoint": "https://e.example",
        "backup_s3_prefix": "nw/",
        "backup_s3_access_key_id": "AKID",
        "backup_s3_secret_access_key": "SECRET",
    }.items():
        monkeypatch.setattr(settings, name, value)
    monkeypatch.setattr(cli_mod, "put_object", fake_put)
    return sent


def test_backup_s3_uploads_a_timestamped_snapshot(
    bucket: list[tuple[S3Target, str, bytes]],
) -> None:
    res = CliRunner().invoke(cli_mod.app, ["backup", "--s3"])
    assert res.exit_code == 0, res.stdout
    ((target, key, body),) = bucket
    assert target == S3Target("wb-backups", "ca-central-1", "AKID", "SECRET", "https://e.example")
    assert re.fullmatch(r"nw/workbench-\d{8}T\d{6}Z\.db", key)
    assert body.startswith(b"SQLite format 3")
    assert f"Backup uploaded: s3://wb-backups/{key} ({len(body)} bytes)" in res.stdout


@pytest.mark.parametrize(
    "missing", ["backup_s3_bucket", "backup_s3_access_key_id", "backup_s3_secret_access_key"]
)
def test_backup_s3_requires_bucket_and_credentials(
    bucket: list[tuple[S3Target, str, bytes]], monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    monkeypatch.setattr(settings, missing, "")
    res = CliRunner().invoke(cli_mod.app, ["backup", "--s3"])
    assert res.exit_code == 2
    assert "WORKBENCH_BACKUP_S3_SECRET_ACCESS_KEY" in res.output
    assert bucket == []


@pytest.mark.parametrize(
    "error", [RuntimeError("S3 refused"), ValueError("not https"), httpx.ConnectError("down")]
)
def test_backup_s3_reports_a_failed_upload(
    bucket: list[tuple[S3Target, str, bytes]], monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    def failing(*_: Any) -> str:
        raise error

    monkeypatch.setattr(cli_mod, "put_object", failing)
    res = CliRunner().invoke(cli_mod.app, ["backup", "--s3"])
    assert res.exit_code == 1
    assert f"Backup upload failed: {error}" in res.stdout
