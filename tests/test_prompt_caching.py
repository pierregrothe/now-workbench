# tests/test_prompt_caching.py
# Otto replays conversations byte for byte, caches its prefix, compacts and counts tokens.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Standing checks for ADR-023: a cache-breaking change to prompt assembly fails here."""

import copy
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient

from now_workbench.domains.conversations.models import ChatMessageRecord
from now_workbench.domains.conversations.repository import ThreadRepository
from now_workbench.interfaces.ai.conversation import replay_conversation
from now_workbench.interfaces.api import replies as replies_api
from now_workbench.interfaces.api.app import create_app
from now_workbench.platform.config.settings import settings
from now_workbench.platform.db.session import db_session


@dataclass
class _Block:
    type: str
    text: str = ""
    id: str = ""
    name: str = ""
    input: dict[str, Any] = field(default_factory=dict)
    content: str | None = None


@dataclass
class _Usage:
    input_tokens: int = 1000
    output_tokens: int = 200
    cache_creation_input_tokens: int = 300
    cache_read_input_tokens: int = 5000
    iterations: list[Any] = field(default_factory=list)


@dataclass
class _Resp:
    content: list[Any]
    stop_reason: str = "end_turn"
    usage: _Usage = field(default_factory=_Usage)


class _ScriptedMessages:
    def __init__(self, script: list[_Resp]) -> None:
        self.script = script
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _Resp:
        self.calls.append(copy.deepcopy(kwargs))
        return self.script.pop(0)


class _ScriptedClaude:
    def __init__(self, script: list[_Resp]) -> None:
        self.messages = _ScriptedMessages(script)


def _install(monkeypatch: pytest.MonkeyPatch, script: list[_Resp]) -> _ScriptedClaude:
    fake = _ScriptedClaude(script)
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test-0000")
    monkeypatch.setattr(replies_api, "make_client", lambda _key: fake)
    return fake


def _no_markers(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = copy.deepcopy(messages)
    for m in out:
        if isinstance(m["content"], list):
            for b in m["content"]:
                b.pop("cache_control", None)
    return out


def test_post_thread_message_replays_the_previous_exchange_byte_for_byte(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Question 2 starts with exactly what question 1 sent and received (cache prefix)."""
    tool_call = _Block("tool_use", id="t1", name="list_bundles", input={})
    fake = _install(
        monkeypatch,
        [
            _Resp([_Block("text", text="Checking."), tool_call], "tool_use"),
            _Resp([_Block("text", text="You have bundles.")]),
            _Resp([_Block("text", text="Second answer.")]),
        ],
    )
    client = TestClient(create_app())
    thread = client.post("/api/threads", json={"title": "t"}).json()["id"]
    client.post(f"/api/threads/{thread}/messages", json={"content": "What bundles?"})
    client.post(f"/api/threads/{thread}/messages", json={"content": "And now?"})

    first_run_last = fake.messages.calls[1]["messages"]
    second = fake.messages.calls[2]["messages"]
    expected_prefix = [
        *first_run_last,
        {"role": "assistant", "content": [{"type": "text", "text": "You have bundles."}]},
    ]
    assert _no_markers(second[: len(expected_prefix)]) == _no_markers(expected_prefix)
    assert second[-1] == {"role": "user", "content": "And now?"}
    # The replay carries Otto's real tool use, not a text summary of it.
    assert any(
        isinstance(m["content"], list) and m["content"][-1].get("type") == "tool_use"
        for m in second
    )


def test_request_cache_markers_and_compaction_are_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prefix cached for an hour, automatic tail caching, compaction at the admin threshold."""
    fake = _install(monkeypatch, [_Resp([_Block("text", text="Hi.")])])
    client = TestClient(create_app())
    client.put("/api/limits", json={"compact_at_tokens": 80_000})
    thread = client.post("/api/threads", json={"title": "t"}).json()["id"]
    client.post(f"/api/threads/{thread}/messages", json={"content": "hello"})
    call = fake.messages.calls[0]
    assert call["system"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert call["cache_control"] == {"type": "ephemeral"}
    assert all("cache_control" not in t for t in call["tools"])
    names = [t["name"] for t in call["tools"]]
    assert names == sorted(names)
    assert call["betas"] == ["compact-2026-01-12"]
    edit = call["context_management"]["edits"][0]
    assert edit["type"] == "compact_20260112"
    assert edit["trigger"] == {"type": "input_tokens", "value": 80_000}
    assert "Do not call any tools" in edit["instructions"]
    client.put("/api/limits", json={"compact_at_tokens": 150_000})


def test_post_thread_message_counts_billable_tokens_into_the_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fresh input + output + 1.25 x cache writes + 0.1 x cache reads, per reply."""
    _install(monkeypatch, [_Resp([_Block("text", text="Hi.")])])
    client = TestClient(create_app())
    thread = client.post("/api/threads", json={"title": "t"}).json()["id"]
    res = client.post(f"/api/threads/{thread}/messages", json={"content": "hello"})
    usage = res.json()[-1]["widget_data"]["usage"]
    assert usage["cache_read"] == 5000 and usage["cache_write"] == 300
    assert usage["billable"] == 1000 + 200 + 375 + 500
    meta = client.get(f"/api/threads/{thread}").json()
    assert meta["tokens_used"] == 2075


def test_post_thread_message_keeps_compaction_blocks_for_the_next_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A compaction summary is stored and sent back (the API then skips what precedes it)."""
    compaction = _Block("compaction", content="Summary: user listed bundles.")
    iterations = [
        type("It", (), {"type": "compaction", "input_tokens": 90_000, "output_tokens": 800}),
        type("It", (), {"type": "message", "input_tokens": 900, "output_tokens": 50}),
    ]
    fake = _install(
        monkeypatch,
        [
            _Resp(
                [compaction, _Block("text", text="Continuing.")],
                usage=_Usage(iterations=iterations),
            ),
            _Resp([_Block("text", text="Next.")]),
        ],
    )
    client = TestClient(create_app())
    thread = client.post("/api/threads", json={"title": "t"}).json()["id"]
    first = client.post(f"/api/threads/{thread}/messages", json={"content": "long chat"}).json()
    assert first[-1]["widget_data"]["usage"]["compactions"] == 1
    assert first[-1]["widget_data"]["usage"]["input"] == 90_900
    client.post(f"/api/threads/{thread}/messages", json={"content": "go on"})
    replayed = fake.messages.calls[1]["messages"]
    blocks = [b for m in replayed if isinstance(m["content"], list) for b in m["content"]]
    assert {"type": "compaction", "content": "Summary: user listed bundles."} in blocks


def test_replay_conversation_handles_legacy_text_files_and_role_order() -> None:
    """Replies without a transcript go back as text; leading assistant turns are dropped."""
    history = [
        ChatMessageRecord(id="w", thread_id="t", role="assistant", content="Welcome"),
        ChatMessageRecord(id="u1", thread_id="t", role="user", content="read this"),
        ChatMessageRecord(id="a1", thread_id="t", role="assistant", content="old text reply"),
        ChatMessageRecord(id="u2", thread_id="t", role="user", content="next"),
        ChatMessageRecord(id="u3", thread_id="t", role="user", content="and more"),
        ChatMessageRecord(id="e", thread_id="t", role="user", content="   "),
        ChatMessageRecord(id="a2", thread_id="t", role="assistant", content="ignored"),
    ]
    transcript = [{"role": "assistant", "content": [{"type": "text", "text": "exact"}]}]
    files = {"u1": [{"type": "document", "source": {"type": "text", "data": "x"}}]}
    out = replay_conversation(history, {"a2": transcript}, files)
    assert [m["role"] for m in out] == ["user", "assistant", "user", "assistant"]
    assert out[0]["content"][0]["type"] == "document"
    assert out[1]["content"] == "old text reply"
    assert out[2]["content"] == "next\nand more"
    assert out[3]["content"] == [{"type": "text", "text": "exact"}]


def test_list_transcripts_is_private_to_the_owner() -> None:
    """Another owner never reads a conversation's transcripts."""
    from now_workbench.domains.conversations.models import ChatThreadCreate
    from now_workbench.platform.owner import owner_scope

    with db_session() as conn:
        thread_repo = ThreadRepository(conn)
        thread_repo.create_thread(ChatThreadCreate(id="tt", title="t"))
        thread_repo.add_message(
            ChatMessageRecord(id="m1", thread_id="tt", role="assistant", content="a"),
            transcript=[{"role": "assistant", "content": "a"}],
        )
        assert list(thread_repo.list_transcripts("tt")) == ["m1"]
        with owner_scope("someone@else.com"):
            assert thread_repo.list_transcripts("tt") == {}


def test_run_agent_signed_compaction_block_and_trailing_user_turn_are_kept() -> None:
    """A signed compaction block keeps its signature; a question joins a trailing user turn."""
    from now_workbench.interfaces.ai.agent import run_agent

    @dataclass
    class _Signed:
        type: str = "compaction"
        content: str = "Summary."
        signature: str = "sig-1"

    fake = _ScriptedClaude([_Resp([_Signed(), _Block("text", text="ok")])])
    prior = [{"role": "user", "content": "unanswered earlier question"}]
    with db_session() as conn:
        resp = run_agent("now this", [], conn, fake, "claude-test", prior=prior)
    sent = fake.messages.calls[0]["messages"]
    assert sent == [{"role": "user", "content": "unanswered earlier question\nnow this"}]
    assert resp.transcript[0]["content"][0] == {
        "type": "compaction",
        "content": "Summary.",
        "signature": "sig-1",
    }
