# tests/test_deepfix_agent_run.py
# Regression tests for run_agent error propagation inside a running event loop
# Author: Pierre Grothe
# Date: 2026-11-06
"""run_agent must not swallow AgentUnavailableError when called inside a running loop."""

from typing import Any

import pytest

from now_workbench.ai.agent import AgentUnavailableError, run_agent
from now_workbench.db import db_session


class _BrokenMessages:
    def create(self, **_kwargs: Any) -> Any:
        raise ValueError("boom")


class _BrokenClient:
    messages = _BrokenMessages()


async def test_run_agent_running_loop_fake_mode_propagates_unavailable_error() -> None:
    with db_session() as repo, pytest.raises(AgentUnavailableError, match="boom"):
        run_agent("hi", [], repo, _BrokenClient(), "claude-test", fake_mode=True)
