# tests/test_cov_api_2.py
# Coverage tests for threads, attachments, app websockets, setup, team, profile, instances.
# Author: Pierre Grothe
# Date: 2026-11-06
"""HTTP and WebSocket coverage for the chat, setup and instance APIs."""

import importlib
import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import jwt
import pytest
from access_kit import _AUD, _KEY, _TEAM, as_user, multi_user_client
from fastapi.testclient import TestClient

from now_workbench.api import threads as threads_api
from now_workbench.api.app import _log_setup_code, create_app
from now_workbench.auth.access import ACCESS_HEADER, AccessValidator
from now_workbench.config.settings import settings
from now_workbench.db import db_session

app_module = importlib.import_module("now_workbench.api.app")
PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"0" * 32


@dataclass
class _Block:
    type: str
    text: str = ""
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class _Resp:
    content: list[_Block]
    stop_reason: str = "end_turn"


class _TextMessages:
    def create(self, **_kwargs: Any) -> _Resp:
        return _Resp([_Block("text", text="Hello from fake Claude")])


class _BrokenMessages:
    def create(self, **_kwargs: Any) -> _Resp:
        raise RuntimeError("claude is down")


class _FakeClient:
    def __init__(self, messages: Any) -> None:
        self.messages = messages

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None


def _no_client(_key: str) -> Any:
    raise RuntimeError("claude is down")


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def _thread(client: TestClient) -> str:
    return str(client.post("/api/threads", json={"title": "T"}).json()["id"])


# --- threads ----------------------------------------------------------------------------


def test_list_threads_after_deleting_default_thread_stays_empty(client: TestClient) -> None:
    """Deleting the seeded default thread must not bring it back on the next listing."""
    threads = client.get("/api/threads").json()
    assert len(threads) == 1
    assert client.delete(f"/api/threads/{threads[0]['id']}").status_code == 200
    assert client.get("/api/threads").json() == []


def test_post_thread_message_runs_autonomous_action_without_agent(client: TestClient) -> None:
    """A verify request is executed by the autonomous action path (no Claude key)."""
    thread = _thread(client)
    res = client.post(
        f"/api/threads/{thread}/messages",
        json={"content": "please verify auth on my instances"},
    )
    assert res.status_code == 200
    assert res.json()[-1]["role"] == "assistant"
    assert res.json()[-1]["widget_type"] == "generative_tiles"


def test_post_thread_message_agent_failure_returns_diagnostic_tiles(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When Claude fails outside fake mode, Otto answers with diagnostic tiles."""
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test-0000")
    monkeypatch.setattr(threads_api, "make_client", _no_client)
    thread = _thread(client)
    res = client.post(f"/api/threads/{thread}/messages", json={"content": "hello"})
    assert res.status_code == 200
    last = res.json()[-1]
    assert last["widget_type"] == "generative_tiles"
    assert "claude is down" in last["content"] or "claude is down" in str(last["widget_data"])


def test_post_thread_message_agent_failure_in_fake_mode_falls_back(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In simulated mode a failing agent falls back to the built-in tile answers."""
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test-0000")
    monkeypatch.setattr(threads_api, "make_client", lambda _k: _FakeClient(_BrokenMessages()))
    client.put("/api/settings", json={"sdk_fake_mode": True})
    thread = _thread(client)
    res = client.post(f"/api/threads/{thread}/messages", json={"content": "hello"})
    assert res.status_code == 200
    assert res.json()[-1]["role"] == "assistant"


def test_post_thread_message_worker_crash_streams_json_detail(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If saving the turn crashes, the stream still ends with a JSON error body."""

    def boom(*_a: Any, **_k: Any) -> None:
        raise RuntimeError("disk full")

    monkeypatch.setattr(threads_api, "_save_turn", boom)
    thread = _thread(client)
    res = client.post(f"/api/threads/{thread}/messages", json={"content": "hi"})
    assert res.json() == {"detail": "Otto could not answer: disk full"}


# --- attachments ------------------------------------------------------------------------


def test_upload_attachment_chunked_body_over_cap_is_413(client: TestClient) -> None:
    """A body without Content-Length is cut off as soon as it exceeds the file cap."""
    client.put("/api/limits", json={"max_file_mb": 1})
    thread = _thread(client)

    def body() -> Iterator[bytes]:
        for _ in range(3):
            yield b"a" * (512 * 1024)

    res = client.post(
        f"/api/threads/{thread}/attachments", params={"filename": "big.txt"}, content=body()
    )
    assert res.status_code == 413


def test_upload_attachment_unknown_thread_is_404(client: TestClient) -> None:
    """Uploading to a thread that does not exist is refused."""
    res = client.post("/api/threads/ghost/attachments", params={"filename": "a.txt"}, content=b"x")
    assert res.status_code == 404


def test_upload_attachment_after_token_budget_is_409(client: TestClient) -> None:
    """Once the conversation used its token budget, files are refused too."""
    client.put("/api/limits", json={"max_conversation_tokens": 50_000})
    thread = _thread(client)
    with db_session() as repo:
        repo.add_thread_tokens(thread, 50_000)
    res = client.post(
        f"/api/threads/{thread}/attachments", params={"filename": "a.txt"}, content=b"x"
    )
    assert res.status_code == 409
    assert "budget" in res.json()["detail"]


def test_attachment_routes_unknown_ids_are_404(client: TestClient) -> None:
    """Download and removal of a missing or foreign attachment return 404."""
    thread = _thread(client)
    other = _thread(client)
    att = client.post(
        f"/api/threads/{thread}/attachments", params={"filename": "a.txt"}, content=b"hello"
    ).json()
    assert client.get(f"/api/threads/{thread}/attachments/nope").status_code == 404
    assert client.get(f"/api/threads/{other}/attachments/{att['id']}").status_code == 404
    assert client.delete(f"/api/threads/{other}/attachments/{att['id']}").status_code == 404
    assert client.delete(f"/api/threads/{thread}/attachments/nope").status_code == 404
    assert client.get(f"/api/threads/{thread}/attachments/{att['id']}").content == b"hello"


# --- app: setup code log, tiles, websocket ----------------------------------------------


def test_log_setup_code_writes_code_to_server_log(caplog: pytest.LogCaptureFixture) -> None:
    """The default announcer writes the readable code to the uvicorn error log."""
    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        _log_setup_code("ABCD-EFGH")
    assert "FIRST-RUN SETUP CODE: ABCD-EFGH" in caplog.text


def test_query_generative_ui_executes_autonomous_action(client: TestClient) -> None:
    """The tiles endpoint returns the autonomous action's response when one matches."""
    res = client.post("/api/ai/tiles", json={"query": "verify auth on all instances"})
    assert res.status_code == 200
    assert res.json()["summary"]


def _ws_collect(client: TestClient, payload: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with client.websocket_connect("/ws/otto") as ws:
        ws.send_json(payload)
        while True:
            msg = ws.receive_json()
            out.append(msg)
            if msg == {"type": "done"} or (msg["type"] == "error" and "message" in msg):
                return out


@pytest.fixture
def ws_claude(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test-0000")
    monkeypatch.setattr(app_module, "make_async_client", lambda _k: _FakeClient(_TextMessages()))


@pytest.mark.usefixtures("ws_claude")
def test_ws_otto_agent_stream_persists_turn_in_thread(client: TestClient) -> None:
    """With a key the agent streams chunks and saves both messages in the thread."""
    thread = _thread(client)
    out = _ws_collect(client, {"prompt": "hi there", "thread_id": thread})
    assert any(m["type"] == "chunk" and "Hello from fake Claude" in m["text"] for m in out)
    assert out[-1] == {"type": "done"}
    saved = client.get(f"/api/threads/{thread}/messages").json()
    assert [m["role"] for m in saved] == ["user", "assistant"]


@pytest.mark.usefixtures("ws_claude")
def test_ws_otto_agent_stream_without_thread_does_not_persist(client: TestClient) -> None:
    """Without a thread id the stream completes and nothing is stored."""
    out = _ws_collect(client, {"prompt": "hi there"})
    assert out[-1] == {"type": "done"}


@pytest.mark.usefixtures("ws_claude")
def test_ws_otto_unknown_thread_sends_error(client: TestClient) -> None:
    """A thread id that does not exist yields an error frame."""
    out = _ws_collect(client, {"prompt": "hi", "thread_id": "ghost"})
    assert out == [{"type": "error", "message": "Thread not found."}]


@pytest.mark.usefixtures("ws_claude")
def test_ws_otto_token_budget_sends_error(client: TestClient) -> None:
    """A conversation over its token budget gets the budget message over the socket."""
    client.put("/api/limits", json={"max_conversation_tokens": 50_000})
    thread = _thread(client)
    with db_session() as repo:
        repo.add_thread_tokens(thread, 50_000)
    out = _ws_collect(client, {"prompt": "second", "thread_id": thread})
    assert out[0]["type"] == "error"
    assert "budget" in out[0]["message"]


# --- setup ------------------------------------------------------------------------------


def _validator() -> AccessValidator:
    return AccessValidator(_TEAM, _AUD, key_resolver=lambda _t: _KEY.public_key())


def test_complete_setup_local_mode_is_409(client: TestClient) -> None:
    """Local mode has no setup to complete."""
    res = client.post("/api/setup", json={"code": "ABCD-EFGH"})
    assert res.status_code == 409
    assert "Local mode" in res.json()["detail"]


def test_complete_setup_wrong_codes_then_lockout_and_missing_code() -> None:
    """Wrong code 400, fifth miss 429 (new code), and no active code 409."""
    codes: list[str] = []
    app = create_app(access_validator=_validator(), announce_setup_code=codes.append)
    me = as_user("first@example.com")
    with TestClient(app) as c:
        statuses = [
            c.post("/api/setup", json={"code": "WRONGWRONG"}, headers=me).status_code
            for _ in range(5)
        ]
        assert statuses == [400, 400, 400, 400, 429]
        assert len(codes) == 2
        app.state.setup_codes.clear()
        res = c.post("/api/setup", json={"code": "WRONGWRONG"}, headers=me)
        assert res.status_code == 409
        assert "No setup code" in res.json()["detail"]
        app.state.setup_codes.issue()
        ok = c.post("/api/setup", json={"code": codes[-1]}, headers=me)
        assert ok.status_code == 200
        assert ok.json()["has_role"] is True


# --- team / profile ---------------------------------------------------------------------


def test_remove_member_last_admin_is_409() -> None:
    """The only administrator cannot be removed."""
    with multi_user_client("admin@example.com", ("sc@example.com",)) as c:
        res = c.delete("/api/team/admin@example.com", headers=as_user("admin@example.com"))
        assert res.status_code == 409
        gone = c.delete("/api/team/sc@example.com", headers=as_user("admin@example.com"))
        assert gone.status_code == 200
        missing = c.delete("/api/team/nobody@example.com", headers=as_user("admin@example.com"))
        assert missing.status_code == 404


def test_upload_avatar_chunked_body_over_2mb_is_413(client: TestClient) -> None:
    """A body with no declared length is still rejected after it is read."""

    def body() -> Iterator[bytes]:
        yield PNG_HEADER
        yield b"0" * (2 * 1024 * 1024 + 1)

    res = client.put("/api/profile/avatar", content=body())
    assert res.status_code == 413


# --- instances --------------------------------------------------------------------------


def test_test_all_instances_reports_each_instance(client: TestClient) -> None:
    """test-all verifies every instance (simulated) and summarizes the outcome."""
    res = client.post("/api/instances/test-all", params={"fake_mode": "true"})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["results"][0]["id"] == "default-instance"


def test_cleanup_unauthenticated_instances_removes_failed_ones(client: TestClient) -> None:
    """A not-authenticated instance is deleted and the remaining one becomes default."""
    with db_session() as repo:
        repo.conn.execute("UPDATE instances SET status = 'failed';")
        repo.conn.commit()
    body = client.post("/api/instances/cleanup").json()
    assert body["deleted_ids"] == ["default-instance"]
    assert body["remaining_count"] == 0


def test_validator_token_helper_matches_access_kit() -> None:
    """Sanity check that the helper token verifies against the kit's validator."""
    now = int(time.time())
    token = jwt.encode(
        {"aud": _AUD, "iss": f"https://{_TEAM}", "iat": now, "exp": now + 60, "email": "z@e.com"},
        _KEY,
        algorithm="RS256",
    )
    assert _validator().email(token) == "z@e.com"
    assert as_user("z@e.com")[ACCESS_HEADER]
