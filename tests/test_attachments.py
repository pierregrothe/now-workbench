# tests/test_attachments.py
# Files attached to conversations, the limits administrators set, and what Claude receives.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for ADR-021 attachments and conversation limits."""

import base64
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from access_kit import as_user, multi_user_client
from fastapi.testclient import TestClient

from now_workbench.domains.conversations.attachment_repository import ChatRepository
from now_workbench.domains.conversations.files import (
    LimitReachedError,
    check_can_ask,
    detect_media_type,
)
from now_workbench.domains.conversations.models import ChatThreadRecord, ConversationLimits
from now_workbench.domains.conversations.repository import ThreadRepository
from now_workbench.interfaces.api import threads as threads_api
from now_workbench.interfaces.api.app import create_app
from now_workbench.platform.config.settings import settings
from now_workbench.platform.db.session import db_session

PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


@dataclass
class _Block:
    type: str
    text: str = ""
    input: dict[str, Any] = field(default_factory=dict)


@dataclass
class _Resp:
    content: list[_Block]
    stop_reason: str = "end_turn"


class _FakeMessages:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _Resp:
        self.calls.append(kwargs)
        return _Resp([_Block("text", text="I read your file.")])


class _FakeClaude:
    def __init__(self) -> None:
        self.messages = _FakeMessages()


@pytest.fixture
def claude(monkeypatch: pytest.MonkeyPatch) -> _FakeClaude:
    """A configured key and an in-memory Claude that records what it was sent."""
    fake = _FakeClaude()
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test-0000")
    monkeypatch.setattr(threads_api, "make_client", lambda _key: fake)
    return fake


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def _thread(client: TestClient) -> str:
    return str(client.post("/api/threads", json={"title": "Files"}).json()["id"])


def _upload(client: TestClient, thread: str, name: str, data: bytes) -> Any:
    return client.post(
        f"/api/threads/{thread}/attachments", params={"filename": name}, content=data
    )


def test_detect_media_type_trusts_bytes_not_names() -> None:
    """A PDF named .png is a PDF; binary named .txt is refused."""
    assert detect_media_type(PDF, "x.png") == "application/pdf"
    assert detect_media_type(PNG, "x.pdf") == "image/png"
    assert detect_media_type(b"GIF89a....", "a") == "image/gif"
    assert detect_media_type(b"hello\n", "notes.md") == "text/plain"
    with pytest.raises(ValueError):
        detect_media_type(b"\x00\x01binary", "data.txt")
    with pytest.raises(ValueError):
        detect_media_type(b"plain words", "script.exe")


def test_upload_attachment_kinds_and_refusals(client: TestClient) -> None:
    """PDF, image and text are accepted; other files are refused with 415."""
    thread = _thread(client)
    assert _upload(client, thread, "brief.pdf", PDF).json()["media_type"] == "application/pdf"
    assert _upload(client, thread, "shot.png", PNG).json()["media_type"] == "image/png"
    assert _upload(client, thread, "notes.md", b"# Notes").json()["media_type"] == "text/plain"
    assert _upload(client, thread, "tool.exe", b"MZ\x00\x00").status_code == 415
    listed = client.get(f"/api/threads/{thread}/attachments").json()
    assert [a["filename"] for a in listed] == ["brief.pdf", "shot.png", "notes.md"]


def test_upload_attachment_enforces_admin_limits(client: TestClient) -> None:
    """Per-file size, file count and conversation total all come from the admin setting."""
    limits = {"max_file_mb": 1, "max_conversation_mb": 2, "max_files": 3}
    assert client.put("/api/limits", json=limits).status_code == 200
    thread = _thread(client)
    big = PDF + b"0" * (1024 * 1024)
    assert _upload(client, thread, "big.pdf", big).status_code == 413
    near = PDF + b"0" * (900 * 1024)
    assert _upload(client, thread, "a.pdf", near).status_code == 200
    assert _upload(client, thread, "b.pdf", near).status_code == 200
    total = _upload(client, thread, "c.pdf", near)
    assert total.status_code == 413
    assert "total at most 2 MB" in total.json()["detail"]
    assert _upload(client, thread, "d.md", b"x").status_code == 200
    count = _upload(client, thread, "e.md", b"x")
    assert count.status_code == 413
    assert "at most 3 files" in count.json()["detail"]


def test_put_limits_needs_admin() -> None:
    """Consultants read the limits but cannot change them."""
    with multi_user_client("admin@example.com", ("sc@example.com",)) as c:
        sc = as_user("sc@example.com")
        assert c.get("/api/limits", headers=sc).json()["max_file_mb"] == 10
        assert c.put("/api/limits", json={"max_turns": 5}, headers=sc).status_code == 403


def test_post_thread_message_sends_files_to_claude(client: TestClient, claude: _FakeClaude) -> None:
    """Attached files reach Claude as document/image blocks before the question."""
    thread = _thread(client)
    pdf = _upload(client, thread, "brief.pdf", PDF).json()
    png = _upload(client, thread, "shot.png", PNG).json()
    note = _upload(client, thread, "notes.md", b"# Notes").json()
    res = client.post(
        f"/api/threads/{thread}/messages",
        json={"content": "Summarize these", "attachment_ids": [pdf["id"], png["id"], note["id"]]},
    )
    assert res.status_code == 200
    assert res.json()[-1]["content"] == "I read your file."
    sent = claude.messages.calls[0]["messages"][-1]["content"]
    kinds = [(b["type"], b["source"]["type"]) for b in sent[:-1]]
    assert kinds == [("document", "base64"), ("image", "base64"), ("document", "text")]
    assert sent[0]["source"]["media_type"] == "application/pdf"
    assert sent[2]["source"]["data"] == "# Notes"
    assert sent[-1] == {"type": "text", "text": "Summarize these"}

    # A follow-up question still carries the earlier files (they are part of the history).
    client.post(f"/api/threads/{thread}/messages", json={"content": "And the image?"})
    history = claude.messages.calls[1]["messages"]
    assert history[0]["content"][0]["type"] == "document"
    assert history[-1]["content"] == "And the image?"

    # Sent files cannot be removed, and an attachment cannot be sent twice.
    removed = client.delete(f"/api/threads/{thread}/attachments/{pdf['id']}")
    assert removed.status_code == 409
    again = client.post(
        f"/api/threads/{thread}/messages", json={"content": "x", "attachment_ids": [pdf["id"]]}
    )
    assert again.status_code == 404


def test_post_thread_message_without_key_explains_files_need_claude(client: TestClient) -> None:
    """Without a Claude key, attached files are not silently ignored."""
    thread = _thread(client)
    att = _upload(client, thread, "notes.md", b"# Notes").json()
    res = client.post(
        f"/api/threads/{thread}/messages",
        json={"content": "Read this", "attachment_ids": [att["id"]]},
    )
    assert "needs a Claude API key" in res.json()[-1]["content"]


def test_attachments_are_private_and_removable(client: TestClient) -> None:
    """Unsent files can be removed; another person never sees them."""
    thread = _thread(client)
    att = _upload(client, thread, "notes.md", b"# Notes").json()
    download = client.get(f"/api/threads/{thread}/attachments/{att['id']}")
    assert download.headers["content-disposition"].startswith("attachment")
    assert client.delete(f"/api/threads/{thread}/attachments/{att['id']}").json() == {
        "removed": True
    }
    with multi_user_client("admin@example.com", ("sc@example.com",)) as c:
        res = c.get(f"/api/threads/{thread}/attachments", headers=as_user("sc@example.com"))
        assert res.status_code == 404


def test_check_can_ask_token_budget_and_age_limits() -> None:
    """Both caps refuse new questions with a clear reason."""
    limits = ConversationLimits(max_conversation_tokens=50_000, max_age_days=7)
    now = datetime.now(UTC)
    stamp = now.isoformat()
    fresh = ChatThreadRecord(id="t", title="t", created_at=stamp, updated_at=stamp)
    check_can_ask(fresh.model_copy(update={"tokens_used": 49_999}), limits)
    with pytest.raises(LimitReachedError, match="budget of 50,000 tokens"):
        check_can_ask(fresh.model_copy(update={"tokens_used": 50_000}), limits)
    old = fresh.model_copy(update={"created_at": (now - timedelta(days=8)).isoformat()})
    with pytest.raises(LimitReachedError, match="older than 7 days"):
        check_can_ask(old, limits)


def _use_budget(thread: str, tokens: int = 60_000) -> None:
    """Mark a conversation as having used ``tokens`` with Claude."""
    with db_session() as conn:
        ThreadRepository(conn).add_thread_tokens(thread, tokens)


def test_delete_thread_removes_attachment_files(client: TestClient) -> None:
    """Deleting a conversation deletes its files from disk."""
    thread = _thread(client)
    att = _upload(client, thread, "notes.md", b"# Notes").json()
    path = settings.get_data_dir() / "attachments" / att["id"]
    assert path.exists()
    client.delete(f"/api/threads/{thread}")
    assert not path.exists()
    with db_session() as conn:
        assert ChatRepository(conn).get_attachment(att["id"]) is None


def test_post_thread_message_slow_reply_keeps_the_connection_alive(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A long reply streams spaces first (beating proxy timeouts), then valid JSON."""
    import time

    def slow_reply(*_args: object, **_kwargs: object) -> object:
        time.sleep(0.35)
        return threads_api._Reply("Done after a while.", None, {})

    monkeypatch.setattr(threads_api, "_KEEPALIVE_S", 0.1)
    monkeypatch.setattr(threads_api, "_build_contextual_reply", slow_reply)
    thread = _thread(client)
    res = client.post(f"/api/threads/{thread}/messages", json={"content": "long job"})
    assert res.status_code == 200
    assert res.text.startswith(" ")
    assert res.json()[-1]["content"] == "Done after a while."


def test_post_thread_message_confirmation_is_not_blocked_by_the_token_budget(
    client: TestClient,
) -> None:
    """Over the budget, confirming a pending action still goes through; questions do not."""
    client.put("/api/limits", json={"max_conversation_tokens": 50_000})
    thread = _thread(client)
    _use_budget(thread)
    blocked = client.post(f"/api/threads/{thread}/messages", json={"content": "q2"})
    assert blocked.status_code == 409
    assert "budget" in blocked.json()["detail"]
    confirm = client.post(
        f"/api/threads/{thread}/messages",
        json={
            "content": "Confirmed: nothing",
            "widget_type": "tool_confirm",
            "widget_data": {"tool": "no_such_tool", "input": {}},
        },
    )
    assert confirm.status_code == 200
    client.put("/api/limits", json={"max_conversation_tokens": 2_000_000})
