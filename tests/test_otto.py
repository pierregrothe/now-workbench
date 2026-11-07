"""Tests for Otto AI Copilot client and WebSocket endpoint."""

import pytest
from fastapi.testclient import TestClient

from now_workbench.interfaces.ai.client import OttoClient
from now_workbench.interfaces.api.app import create_app


@pytest.mark.asyncio
async def test_otto_client_simulation_mode() -> None:
    """Verify OttoClient generates deterministic simulated response when API key is missing."""
    client = OttoClient(api_key="")
    chunks: list[str] = []
    async for chunk in client.stream_chat(
        messages=[{"role": "user", "content": "How do I fix a build error in Fluent SDK?"}],
        context={"active_bundle": "sample-ai-assistant"},
    ):
        chunks.append(chunk)

    full_text = "".join(chunks)
    assert "Otto" in full_text
    assert "simulation mode" in full_text
    assert "Fluent SDK" in full_text

    # Test general inquiry path
    general_chunks: list[str] = []
    async for chunk in client.stream_chat(
        messages=[{"role": "user", "content": "Tell me about personas"}],
    ):
        general_chunks.append(chunk)
    gen_text = "".join(general_chunks)
    assert "Tell me about personas" in gen_text

    # Test fluent schema inquiry path
    fluent_chunks: list[str] = []
    async for chunk in client.stream_chat(
        messages=[{"role": "user", "content": "Explain Fluent schema declaration"}],
    ):
        fluent_chunks.append(chunk)
    fluent_text = "".join(fluent_chunks)
    assert "Fluent SDK schemas are declared" in fluent_text

    # Test demohub inquiry path
    demohub_chunks: list[str] = []
    async for chunk in client.stream_chat(
        messages=[{"role": "user", "content": "What is DemoHub?"}],
    ):
        demohub_chunks.append(chunk)
    demohub_text = "".join(demohub_chunks)
    assert "DemoHub vs Now Workbench Parity" in demohub_text

    # Test instance and settings inquiry path
    instance_chunks: list[str] = []
    async for chunk in client.stream_chat(
        messages=[{"role": "user", "content": "How do I configure target instance settings?"}],
    ):
        instance_chunks.append(chunk)
    instance_text = "".join(instance_chunks)
    assert "Instance & Configuration Guidance" in instance_text


@pytest.mark.asyncio
async def test_otto_client_streaming_success() -> None:
    """Verify live Claude streaming loop yields tokens correctly."""
    from collections.abc import AsyncIterator
    from typing import Any

    class FakeClaudeStream:
        def __init__(self, chunks: list[str]) -> None:
            self._chunks = chunks

        @property
        def text_stream(self) -> AsyncIterator[str]:
            async def _generator() -> AsyncIterator[str]:
                for c in self._chunks:
                    yield c

            return _generator()

        async def __aenter__(self) -> FakeClaudeStream:
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: Any,
        ) -> None:
            pass

    class FakeClaudeMessages:
        def __init__(self, chunks: list[str]) -> None:
            self._chunks = chunks

        def stream(self, **kwargs: Any) -> FakeClaudeStream:
            return FakeClaudeStream(self._chunks)

    class FakeAnthropicClient:
        def __init__(self, chunks: list[str]) -> None:
            self.messages = FakeClaudeMessages(chunks)

    fake_client = FakeAnthropicClient(["Hello ", "from ", "Claude!"])
    client = OttoClient(api_key="test-key", client=fake_client)

    chunks: list[str] = []
    async for chunk in client.stream_chat(
        messages=[{"role": "user", "content": "Explain tables"}],
        context={"active_bundle": "sample-ai-assistant"},
    ):
        chunks.append(chunk)

    assert "".join(chunks) == "Hello from Claude!"


@pytest.mark.asyncio
async def test_otto_client_api_error_handling() -> None:
    """Verify error catching when Claude client encounters connection issues."""
    client = OttoClient(api_key="test-api-key")
    error_chunks: list[str] = []
    async for chunk in client.stream_chat(
        messages=[{"role": "user", "content": "Hello"}],
    ):
        error_chunks.append(chunk)

    full_error = "".join(error_chunks)
    assert "error contacting Claude API" in full_error


def test_ws_otto_chat_endpoint() -> None:
    """Verify /ws/otto WebSocket streaming endpoint connects and streams response chunks."""
    app = create_app()
    client = TestClient(app)
    with client.websocket_connect("/ws/otto") as websocket:
        websocket.send_json(
            {
                "messages": [{"role": "user", "content": "Explain Fluent tables"}],
                "context": {"bundle": "sample"},
            }
        )
        received_chunks: list[str] = []
        is_done = False
        while not is_done:
            data = websocket.receive_json()
            if data.get("type") == "chunk":
                received_chunks.append(data.get("text", ""))
            elif data.get("type") == "done":
                is_done = True

        combined = "".join(received_chunks)
        assert len(combined) > 0
        assert "Otto" in combined
