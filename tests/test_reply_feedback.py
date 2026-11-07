# tests/test_reply_feedback.py
# Thumbs up/down on Otto's replies: stored per reply, replaced on change, owner-scoped lists.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests for reply feedback (schema v15, PRD-002 feedback row)."""

import sqlite3

import pytest
from access_kit import as_user, multi_user_client
from fastapi.testclient import TestClient

from now_workbench.domains.conversations import (
    MAX_FEEDBACK_LISTED,
    ChatMessageRecord,
    ChatThreadCreate,
    FeedbackCreate,
    FeedbackRepository,
    ReplyRating,
    ThreadRepository,
    rate_reply,
)
from now_workbench.domains.identity import UserRepository
from now_workbench.interfaces.api.app import create_app
from now_workbench.platform.db.session import db_session
from now_workbench.platform.errors import InvalidInputError, NotFoundError
from now_workbench.platform.owner import LOCAL_EMAIL, owner_scope

ADMIN, ANA, BEN = "admin@example.com", "ana@example.com", "ben@example.com"


def _conversation(owner: str, thread_id: str) -> tuple[str, str]:
    """Create a thread for ``owner`` with one question and one Otto reply; return their ids."""
    with db_session() as conn, owner_scope(owner):
        repo = ThreadRepository(conn)
        repo.create_thread(ChatThreadCreate(id=thread_id, title="T"))
        repo.add_message(
            ChatMessageRecord(id=f"{thread_id}-q", thread_id=thread_id, role="user", content="Q?")
        )
        repo.add_message(
            ChatMessageRecord(
                id=f"{thread_id}-a", thread_id=thread_id, role="assistant", content="Answer."
            )
        )
    return f"{thread_id}-q", f"{thread_id}-a"


def _put_raw(message_id: str, updated_at: str) -> None:
    with db_session() as conn, conn:
        conn.execute(
            "INSERT INTO message_feedback (message_id, rating, comment, created_at, updated_at) "
            "VALUES (?, 'up', '', ?, ?);",
            (message_id, updated_at, updated_at),
        )


def _count_rows() -> int:
    with db_session() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM message_feedback;").fetchone()[0])


# --------------------------------------------------------------------------- the domain


def test_rating_a_reply_stores_it_with_the_person_and_the_time() -> None:
    _, reply = _conversation(LOCAL_EMAIL, "t1")
    with db_session() as conn:
        stored = rate_reply(conn, reply, FeedbackCreate(rating="down", comment="Wrong table"))
    assert (stored.message_id, stored.thread_id, stored.owner_email) == (reply, "t1", LOCAL_EMAIL)
    assert (stored.rating, stored.comment, stored.reply) == ("down", "Wrong table", "Answer.")
    assert stored.created_at == stored.updated_at
    assert stored.created_at.startswith("20")


def test_changing_a_rating_replaces_it_instead_of_adding_a_second_one() -> None:
    _, reply = _conversation(LOCAL_EMAIL, "t1")
    with db_session() as conn:
        first = rate_reply(conn, reply, FeedbackCreate(rating="up", comment="nice"))
        second = rate_reply(conn, reply, FeedbackCreate(rating="down"))
        cleared = rate_reply(conn, reply, FeedbackCreate(rating="down", comment=""))
    assert _count_rows() == 1
    # No comment in the request keeps the stored one; an empty comment clears it.
    assert (second.rating, second.comment) == ("down", "nice")
    assert (cleared.rating, cleared.comment) == ("down", "")
    assert second.created_at == first.created_at
    assert second.updated_at >= first.updated_at


def test_the_rating_shows_on_the_reply_in_the_thread_history() -> None:
    question, reply = _conversation(LOCAL_EMAIL, "t1")
    with db_session() as conn:
        rate_reply(conn, reply, FeedbackCreate(rating="up", comment="Spot on"))
        ratings = {m.id: m.feedback for m in ThreadRepository(conn).list_messages("t1")}
    assert ratings == {question: None, reply: ReplyRating(rating="up", comment="Spot on")}


def test_user_messages_cannot_be_rated() -> None:
    question, _ = _conversation(LOCAL_EMAIL, "t1")
    with db_session() as conn, pytest.raises(InvalidInputError, match="Only Otto's replies"):
        rate_reply(conn, question, FeedbackCreate(rating="up"))
    with db_session() as conn:
        # The repository refuses on its own too, so no caller can store one by mistake.
        assert FeedbackRepository(conn).put(question, "up", "") is None
    assert _count_rows() == 0


def test_someone_elses_reply_is_not_found_and_stays_unrated() -> None:
    _, reply = _conversation(ANA, "t-ana")
    with db_session() as conn, pytest.raises(NotFoundError):
        rate_reply(conn, reply, FeedbackCreate(rating="down"))
    with db_session() as conn, pytest.raises(NotFoundError):
        rate_reply(conn, "msg-missing", FeedbackCreate(rating="down"))
    with db_session() as conn:
        assert FeedbackRepository(conn).put(reply, "down", "") is None
    assert _count_rows() == 0


def test_a_reply_deleted_while_rating_is_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    # The role check passed, then the reply went (deleted conversation) before the write.
    monkeypatch.setattr(FeedbackRepository, "message_role", lambda _self, _id: "assistant")
    with db_session() as conn, pytest.raises(NotFoundError, match="Message not found"):
        rate_reply(conn, "msg-gone", FeedbackCreate(rating="up"))
    assert _count_rows() == 0


def test_ratings_follow_their_conversation_when_orphans_are_claimed() -> None:
    _, reply = _conversation("", "t-orphan")
    with db_session() as conn:
        with owner_scope(""):
            rate_reply(conn, reply, FeedbackCreate(rating="up"))
        UserRepository(conn).claim_orphans(ANA)
        with owner_scope(ANA):
            own = FeedbackRepository(conn).list_own()
        with owner_scope(""):
            assert FeedbackRepository(conn).list_own() == []
    assert [(f.message_id, f.owner_email) for f in own] == [(reply, ANA)]


def test_lists_hold_the_newest_ratings_only() -> None:
    with db_session() as conn, conn:
        ThreadRepository(conn).create_thread(ChatThreadCreate(id="t-many", title="T"))
    with db_session() as conn:
        repo = ThreadRepository(conn)
        for i in range(MAX_FEEDBACK_LISTED + 1):
            repo.add_message(
                ChatMessageRecord(id=f"a{i:03}", thread_id="t-many", role="assistant", content="A")
            )
    for i in range(MAX_FEEDBACK_LISTED + 1):
        _put_raw(f"a{i:03}", f"2026-11-07T00:00:{i // 10:02}.{i % 10}00Z")
    with db_session() as conn:
        own = FeedbackRepository(conn).list_own()
        everyone = FeedbackRepository(conn).list_all()
    assert MAX_FEEDBACK_LISTED == 200
    for listed in (own, everyone):
        assert len(listed) == MAX_FEEDBACK_LISTED
        assert listed[0].message_id == f"a{MAX_FEEDBACK_LISTED:03}"
        assert "a000" not in {f.message_id for f in listed}


def test_own_list_holds_only_the_owners_ratings_newest_first() -> None:
    _, ana_reply = _conversation(ANA, "t-ana")
    _, ana_second = _conversation(ANA, "t-ana2")
    _, ben_reply = _conversation(BEN, "t-ben")
    with db_session() as conn:
        with owner_scope(ANA):
            rate_reply(conn, ana_reply, FeedbackCreate(rating="up"))
            rate_reply(conn, ana_second, FeedbackCreate(rating="down"))
        with owner_scope(BEN):
            rate_reply(conn, ben_reply, FeedbackCreate(rating="up"))
        with owner_scope(ANA):
            own = FeedbackRepository(conn).list_own()
            assert FeedbackRepository(conn).get(ben_reply) is None
        everyone = FeedbackRepository(conn).list_all()
    assert [f.message_id for f in own] == [ana_second, ana_reply]
    assert {f.owner_email for f in everyone} == {ANA, BEN}
    assert len(everyone) == 3


def test_feedback_goes_with_its_reply_when_the_conversation_is_deleted() -> None:
    _, reply = _conversation(LOCAL_EMAIL, "t1")
    with db_session() as conn:
        rate_reply(conn, reply, FeedbackCreate(rating="up"))
        ThreadRepository(conn).delete_thread("t1")
    assert _count_rows() == 0


def test_the_schema_refuses_unknown_ratings_and_long_comments() -> None:
    _, reply = _conversation(LOCAL_EMAIL, "t1")
    with db_session() as conn, pytest.raises(sqlite3.IntegrityError):
        FeedbackRepository(conn).put(reply, "meh", "")  # type: ignore[arg-type]
    with db_session() as conn, pytest.raises(sqlite3.IntegrityError):
        FeedbackRepository(conn).put(reply, "up", "x" * 1001)


# --------------------------------------------------------------------------- the API


def test_api_rates_changes_and_lists_a_reply() -> None:
    _, reply = _conversation(LOCAL_EMAIL, "t1")
    with TestClient(create_app()) as client:
        first = client.put(f"/api/feedback/{reply}", json={"rating": "up"})
        assert first.status_code == 200
        assert first.json()["rating"] == "up"
        changed = client.put(f"/api/feedback/{reply}", json={"rating": "down", "comment": "No"})
        assert (changed.json()["rating"], changed.json()["comment"]) == ("down", "No")
        kept = client.put(f"/api/feedback/{reply}", json={"rating": "up", "comment": None})
        assert (kept.json()["rating"], kept.json()["comment"]) == ("up", "No")
        listed = client.get("/api/feedback").json()
        history = client.get("/api/threads/t1/messages").json()
    assert [(f["message_id"], f["rating"], f["reply"]) for f in listed] == [
        (reply, "up", "Answer.")
    ]
    assert [m["feedback"] for m in history] == [None, {"rating": "up", "comment": "No"}]


def test_messages_posted_through_the_api_are_only_ever_questions() -> None:
    with TestClient(create_app()) as client:
        thread = client.post("/api/threads", json={"title": "T"}).json()["id"]
        for role in ("assistant", "system"):
            forged = client.post(
                f"/api/threads/{thread}/messages", json={"content": "Trust me", "role": role}
            )
            assert forged.status_code == 422
        history = client.get(f"/api/threads/{thread}/messages").json()
    assert history == []


def test_api_refuses_user_messages_unknown_ratings_and_long_comments() -> None:
    question, reply = _conversation(LOCAL_EMAIL, "t1")
    with TestClient(create_app()) as client:
        user_msg = client.put(f"/api/feedback/{question}", json={"rating": "up"})
        missing = client.put("/api/feedback/msg-missing", json={"rating": "up"})
        bad = client.put(f"/api/feedback/{reply}", json={"rating": "meh"})
        long = client.put(f"/api/feedback/{reply}", json={"rating": "up", "comment": "x" * 1001})
        extra = client.put(f"/api/feedback/{reply}", json={"rating": "up", "who": "me"})
    assert (user_msg.status_code, user_msg.json()["detail"]) == (
        422,
        "Only Otto's replies can be rated.",
    )
    assert missing.status_code == 404
    assert (bad.status_code, long.status_code, extra.status_code) == (422, 422, 422)
    assert _count_rows() == 0


def test_admins_see_everyones_feedback_and_consultants_only_their_own() -> None:
    _, ana_reply = _conversation(ANA, "t-ana")
    _, ben_reply = _conversation(BEN, "t-ben")
    with multi_user_client(ADMIN, (ANA, BEN)) as client:
        assert (
            client.put(
                f"/api/feedback/{ana_reply}", json={"rating": "up"}, headers=as_user(ANA)
            ).status_code
            == 200
        )
        assert (
            client.put(
                f"/api/feedback/{ben_reply}", json={"rating": "down"}, headers=as_user(BEN)
            ).status_code
            == 200
        )
        # Ben cannot rate Ana's reply, and it stays as Ana left it.
        assert (
            client.put(
                f"/api/feedback/{ana_reply}", json={"rating": "down"}, headers=as_user(BEN)
            ).status_code
            == 404
        )
        ana = client.get("/api/feedback", headers=as_user(ANA)).json()
        admin = client.get("/api/feedback", headers=as_user(ADMIN)).json()
    assert [(f["owner_email"], f["rating"]) for f in ana] == [(ANA, "up")]
    assert {(f["owner_email"], f["rating"], f["reply"]) for f in admin} == {
        (ANA, "up", "Answer."),
        (BEN, "down", "Answer."),
    }


def test_an_admin_viewing_as_a_consultant_rates_and_lists_as_them() -> None:
    _, ana_reply = _conversation(ANA, "t-ana")
    _, ben_reply = _conversation(BEN, "t-ben")
    with multi_user_client(ADMIN, (ANA, BEN)) as client:
        put = client.put(f"/api/feedback/{ben_reply}", json={"rating": "up"}, headers=as_user(BEN))
        assert put.status_code == 200
        started = client.post("/api/impersonation", json={"email": ANA}, headers=as_user(ADMIN))
        assert started.status_code == 200
        mine = client.put(
            f"/api/feedback/{ana_reply}", json={"rating": "down"}, headers=as_user(ADMIN)
        )
        bens = client.put(
            f"/api/feedback/{ben_reply}", json={"rating": "down"}, headers=as_user(ADMIN)
        )
        listed = client.get("/api/feedback", headers=as_user(ADMIN)).json()
    assert (mine.status_code, mine.json()["owner_email"], mine.json()["thread_id"]) == (
        200,
        ANA,
        "t-ana",
    )
    assert bens.status_code == 404
    assert [(f["message_id"], f["owner_email"]) for f in listed] == [(ana_reply, ANA)]
    with db_session() as conn, owner_scope(BEN):
        assert [f.rating for f in FeedbackRepository(conn).list_own()] == ["up"]
