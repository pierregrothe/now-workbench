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


# --------------------------------------------------------------------------- overrides and API


def test_get_allowance_shows_your_own_standing(team: TestClient) -> None:
    _usage(ANA, _this_month(), inp=25_000)
    own = team.get("/api/usage/allowance", headers=as_user(ANA)).json()
    assert {k: own[k] for k in ("state", "used", "allowance", "percent")} == {
        "state": "ok",
        "used": 25_000,
        "allowance": ALLOWANCE,
        "percent": 25,
    }
    assert re.fullmatch(r"\d{4}-\d{2}-01", own["resets_on"])
    assert team.get("/api/usage/allowance", headers=as_user(ADMIN)).json()["state"] == "exempt"


def test_team_allowances_are_for_administrators(team: TestClient) -> None:
    assert team.get("/api/usage/allowances", headers=as_user(ANA)).status_code == 403
    put = team.put(
        f"/api/usage/allowances/{BEN}", json={"monthly_tokens": 500_000}, headers=as_user(ANA)
    )
    assert put.status_code == 403


def test_set_allowance_override_changes_one_person_and_the_gate(team: TestClient) -> None:
    _usage(ANA, _this_month(), inp=150_000)
    assert _ask(team, ANA).status_code == 429
    rows = team.put(
        f"/api/usage/allowances/{ANA}", json={"monthly_tokens": 300_000}, headers=as_user(ADMIN)
    ).json()
    by_email = {r["email"]: r for r in rows}
    assert {k: by_email[ANA][k] for k in ("used", "allowance", "percent", "overridden")} == {
        "used": 150_000,
        "allowance": 300_000,
        "percent": 50,
        "overridden": True,
    }
    assert by_email[ANA]["state"] == "ok"  # under its own allowance, not the default's
    ben = by_email[BEN]
    assert (ben["used"], ben["allowance"], ben["overridden"], ben["state"]) == (
        0,
        ALLOWANCE,
        False,
        "ok",
    )
    assert by_email[ADMIN]["state"] == "exempt"
    assert _ask(team, ANA).status_code == 200

    _usage(BEN, _this_month(), inp=ALLOWANCE)
    listed = team.get("/api/usage/allowances", headers=as_user(ADMIN)).json()
    assert {r["email"]: r["state"] for r in listed} == {
        ADMIN: "exempt",
        ANA: "ok",
        BEN: "refused",
    }

    back = team.put(
        f"/api/usage/allowances/{ANA}", json={"monthly_tokens": None}, headers=as_user(ADMIN)
    ).json()
    assert {r["email"]: r["overridden"] for r in back}[ANA] is False
    assert _ask(team, ANA).status_code == 429


@pytest.mark.parametrize(
    ("email", "tokens", "status", "detail"),
    [
        (ANA, 99_999, 422, "An allowance must be between 100,000 and 1,000,000,000 tokens."),
        (ANA, 1_000_000_001, 422, "An allowance must be between 100,000 and 1,000,000,000 tokens."),
        ("nobody@example.com", 500_000, 404, "nobody@example.com is not on the team."),
    ],
)
def test_set_allowance_override_refuses_bad_amounts_and_strangers(
    team: TestClient, email: str, tokens: int, status: int, detail: str
) -> None:
    res = team.put(
        f"/api/usage/allowances/{email}", json={"monthly_tokens": tokens}, headers=as_user(ADMIN)
    )
    assert (res.status_code, res.json()["detail"]) == (status, detail)


def test_set_allowance_override_accepts_the_bounds(team: TestClient) -> None:
    for tokens in (100_000, 1_000_000_000):
        res = team.put(
            f"/api/usage/allowances/{ANA}", json={"monthly_tokens": tokens}, headers=as_user(ADMIN)
        )
        assert {r["email"]: r["allowance"] for r in res.json()}[ANA] == tokens


def test_set_allowance_override_records_the_real_administrator_behind_view_as(
    team: TestClient,
) -> None:
    from now_workbench.domains.telemetry import set_allowance_override

    admin_as_ben = AuthUser(
        email=BEN,
        roles=frozenset(Role),
        mode="cloudflare",
        real_email=ADMIN,
        real_roles=frozenset(Role),
    )
    with db_session() as conn:
        set_allowance_override(conn, admin_as_ben, ANA, 400_000)
        row = conn.execute("SELECT updated_by FROM usage_allowances WHERE email = ?", (ANA,))
        assert row.fetchone()[0] == ADMIN


# --------------------------------------------------------------------------- Otto's tools


def test_usage_allowances_tool_lists_everyone(team: TestClient) -> None:
    from now_workbench.interfaces.ai.tools import execute_tool
    from now_workbench.interfaces.ai.tools.base import ToolContext

    _usage(ANA, _this_month(), inp=50_000)
    with db_session() as conn:
        result = execute_tool(ToolContext(conn=conn, user=ADMIN_USER), "usage_allowances", {})
    people = {p["email"]: p for p in result.data["people"]}
    assert (people[ANA]["used"], people[ANA]["percent"]) == (50_000, 50)
    assert result.tiles[0].props["rows"][0][0] in {ADMIN, ANA, BEN}
    assert result.summary == "Claude usage this month for 3 people (billable tokens)."


def test_set_usage_allowance_tool_confirms_then_sets(team: TestClient) -> None:
    from now_workbench.interfaces.ai.tools import execute_tool
    from now_workbench.interfaces.ai.tools.base import ToolContext

    args = {"email": ANA, "monthly_tokens": 2_500_000}
    with db_session() as conn:
        pending = execute_tool(ToolContext(conn=conn, user=ADMIN_USER), "set_usage_allowance", args)
        assert pending.pending
        assert "Set ana@example.com's monthly allowance to 2,500,000." in pending.summary
        done = execute_tool(
            ToolContext(conn=conn, user=ADMIN_USER), "set_usage_allowance", args, confirmed=True
        )
        reset = execute_tool(
            ToolContext(conn=conn, user=ADMIN_USER),
            "set_usage_allowance",
            {"email": ANA, "monthly_tokens": None},
            confirmed=True,
        )
    assert done.summary == "ana@example.com now has 2,500,000 tokens a month."
    assert reset.summary == "ana@example.com now has the default."
