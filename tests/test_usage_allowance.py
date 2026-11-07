# tests/test_usage_allowance.py
# Monthly Claude allowance per person: counted, warned, refused, admins exempt (ADR-031).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests for the usage allowance service, its gate and every Claude entry point."""

import re
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from access_kit import as_user, multi_user_client
from fastapi.testclient import TestClient

from now_workbench.domains.conversations import ChatRepository, ConversationLimits
from now_workbench.domains.identity import AuthUser, Role
from now_workbench.domains.telemetry import WARN_AT_PERCENT, Allowance, check_allowance
from now_workbench.interfaces.api.threads import USAGE_WARNING_HEADER
from now_workbench.platform.db.session import db_session
from now_workbench.platform.owner import owner_scope

SRC = Path(__file__).resolve().parents[1] / "src" / "now_workbench"
ADMIN, ANA, BEN = "admin@example.com", "ana@example.com", "ben@example.com"
ANA_USER = AuthUser(email=ANA, roles=frozenset({Role.SOLUTION_CONSULTANT}), mode="cloudflare")
ADMIN_USER = AuthUser(email=ADMIN, roles=frozenset(Role), mode="cloudflare")
NOW = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
ALLOWANCE = 100_000  # the smallest allowance the settings accept


def _usage(owner: str, at: str, inp: int = 0, out: int = 0, cw: int = 0, cr: int = 0) -> None:
    with db_session() as conn, conn:
        conn.execute(
            "INSERT INTO usage_events (owner_email, actor_email, model, input_tokens, "
            "output_tokens, cache_write, cache_read, created_at) VALUES (?, ?, 'm', ?, ?, ?, ?, ?)",
            (owner, owner, inp, out, cw, cr, at),
        )


def _check(user: AuthUser, now: datetime = NOW, allowance: int = ALLOWANCE) -> Allowance:
    with db_session() as conn, owner_scope(user.email):
        return check_allowance(conn, user, allowance, now)


def _set_allowance(tokens: int) -> None:
    with db_session() as conn:
        ChatRepository(conn).put_conversation_limits(
            ConversationLimits(monthly_allowance_tokens=tokens), updated_by="test"
        )


# --------------------------------------------------------------------------- the service


def test_check_allowance_counts_billable_tokens_this_month_for_the_owner_only() -> None:
    _usage(ANA, "2026-11-01T00:00:00.000Z", inp=100, out=50, cw=8, cr=1000)  # 260 billable
    _usage(ANA, "2026-11-07T11:00:00.000Z", inp=3, cr=5)  # 3.5 -> with the rest, 263.5
    _usage(ANA, "2026-10-31T23:59:59.999Z", inp=10_000)  # last month
    _usage(BEN, "2026-11-02T00:00:00.000Z", inp=10_000)  # someone else
    assert _check(ANA_USER).used == 264  # 263.5 rounds to the nearest token


@pytest.mark.parametrize(
    ("used", "state"),
    [
        (0, "ok"),
        (79_999, "ok"),
        (80_000, "warn"),
        (99_999, "warn"),
        (100_000, "refused"),
        (250_000, "refused"),
    ],
)
def test_check_allowance_warns_at_80_and_refuses_at_100_percent(used: int, state: str) -> None:
    if used:
        _usage(ANA, "2026-11-03T00:00:00.000Z", inp=used)
    standing = _check(ANA_USER)
    assert (standing.state, standing.used, standing.allowance) == (state, used, ALLOWANCE)
    assert WARN_AT_PERCENT == 80


def test_check_allowance_exempts_administrators() -> None:
    _usage(ADMIN, "2026-11-03T00:00:00.000Z", inp=5 * ALLOWANCE)
    standing = _check(ADMIN_USER)
    assert (standing.state, standing.used) == ("exempt", 5 * ALLOWANCE)
    assert standing.message() == ""


@pytest.mark.parametrize(
    ("now", "resets"),
    [
        (NOW, date(2026, 12, 1)),
        (datetime(2026, 12, 31, 23, 59, tzinfo=UTC), date(2027, 1, 1)),
        (datetime(2027, 1, 1, 0, 0, tzinfo=UTC), date(2027, 2, 1)),
    ],
)
def test_check_allowance_resets_on_the_first_of_next_month(now: datetime, resets: date) -> None:
    assert _check(ANA_USER, now=now).resets_on == resets


def test_check_allowance_month_starts_at_utc_midnight() -> None:
    _usage(ANA, "2026-11-30T23:30:00.000Z", inp=50_000)
    # 00:30 on Dec 1 in UTC+1 is 23:30 on Nov 30 in UTC: still November.
    paris = datetime(2026, 12, 1, 0, 30, tzinfo=timezone(timedelta(hours=1)))
    assert _check(ANA_USER, now=paris).used == 50_000


def test_allowance_messages_name_the_use_and_the_reset_date() -> None:
    warn = Allowance(state="warn", used=85_500, allowance=100_000, resets_on=date(2026, 12, 1))
    refused = Allowance(
        state="refused", used=100_000, allowance=100_000, resets_on=date(2026, 12, 1)
    )
    ok = Allowance(state="ok", used=1, allowance=100_000, resets_on=date(2026, 12, 1))
    assert warn.percent == 85
    assert warn.message() == (
        "You have used 85% of your monthly Claude allowance (85,500 of 100,000 tokens). "
        "It resets on December 1."
    )
    assert refused.message() == (
        "You have used your monthly Claude allowance (100,000 tokens). "
        "It resets on December 1; an administrator can raise it."
    )
    assert ok.message() == ""


def test_conversation_limits_default_allowance_is_ten_million() -> None:
    assert ConversationLimits().monthly_allowance_tokens == 10_000_000
    with pytest.raises(ValueError):
        ConversationLimits(monthly_allowance_tokens=99_999)


# --------------------------------------------------------------------------- the entry points


@pytest.fixture
def team() -> Iterator[TestClient]:
    with multi_user_client(ADMIN, (ANA, BEN)) as client:
        _set_allowance(ALLOWANCE)
        yield client


def _ask(client: TestClient, email: str) -> httpx.Response:
    thread = client.post("/api/threads", json={"title": "Q"}, headers=as_user(email)).json()
    return client.post(
        f"/api/threads/{thread['id']}/messages",
        json={"content": "How many instances?"},
        headers=as_user(email),
    )


def _this_month() -> str:
    return datetime.now(UTC).strftime("%Y-%m-03T00:00:00.000Z")


def test_post_thread_message_refuses_a_spent_allowance_with_429(team: TestClient) -> None:
    _usage(ANA, _this_month(), inp=ALLOWANCE)
    with db_session() as conn:
        before = conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0]
    res = _ask(team, ANA)
    assert res.status_code == 429
    detail = res.json()["detail"]
    assert detail.startswith("You have used your monthly Claude allowance (100,000 tokens).")
    with db_session() as conn:
        assert conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0] == before


def test_post_thread_message_carries_the_80_percent_warning(team: TestClient) -> None:
    _usage(ANA, _this_month(), inp=90_000)
    res = _ask(team, ANA)
    assert res.status_code == 200
    warning = res.headers[USAGE_WARNING_HEADER]
    assert re.fullmatch(
        r"You have used 90% of your monthly Claude allowance \(90,000 of 100,000 tokens\)\. "
        r"It resets on [A-Z][a-z]+ 1\.",
        warning,
    )


def test_post_thread_message_below_80_percent_has_no_warning(team: TestClient) -> None:
    res = _ask(team, BEN)
    assert res.status_code == 200
    assert USAGE_WARNING_HEADER not in res.headers


def test_post_thread_message_never_refuses_an_administrator(team: TestClient) -> None:
    _usage(ADMIN, _this_month(), inp=10 * ALLOWANCE)
    res = _ask(team, ADMIN)
    assert res.status_code == 200
    assert USAGE_WARNING_HEADER not in res.headers


def test_post_thread_message_under_view_as_uses_the_viewed_persons_allowance(
    team: TestClient,
) -> None:
    _usage(ANA, _this_month(), inp=ALLOWANCE)
    assert team.post("/api/impersonation", json={"email": ANA}, headers=as_user(ADMIN)).is_success
    assert _ask(team, ADMIN).status_code == 429


def test_ws_otto_refuses_a_spent_allowance_before_any_claude_call(team: TestClient) -> None:
    _usage(ANA, _this_month(), inp=ALLOWANCE)
    with team.websocket_connect("/ws/otto", headers=as_user(ANA)) as ws:
        ws.send_json({"prompt": "hello"})
        msg = ws.receive_json()
    assert msg["type"] == "error"
    assert msg["message"].startswith("You have used your monthly Claude allowance")


def test_ws_otto_sends_the_warning_first(team: TestClient) -> None:
    _usage(ANA, _this_month(), inp=85_000)
    with team.websocket_connect("/ws/otto", headers=as_user(ANA)) as ws:
        ws.send_json({"messages": [{"role": "user", "content": "hi"}]})
        first = ws.receive_json()
    assert first["type"] == "usage_warning"
    assert first["message"].startswith("You have used 85% of your monthly Claude allowance")


def test_every_question_entry_point_passes_the_allowance_gate() -> None:
    """A route that checks the conversation limits before Claude must also check the allowance."""
    entry_points = [
        p for p in (SRC / "interfaces").rglob("*.py") if "check_can_ask(" in p.read_text()
    ]
    assert {p.name for p in entry_points} == {"threads.py", "otto_ws.py", "attachments.py"}
    for path in entry_points:
        if path.name == "attachments.py":  # uploads files; it never calls Claude
            continue
        assert "enforce_allowance(" in path.read_text(), path
