# tests/test_deepfix_plugin_install.py
# Regression tests: install_plugin must verify the instance instead of claiming success
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for PluginManager.install_plugin verify-don't-claim behaviour."""

import httpx

from now_workbench.db import DatabaseRepository, InstanceCreate, InstanceRecord, init_db
from now_workbench.plugins.manager import PluginManager


def _setup(
    handler: httpx.MockTransport,
) -> tuple[PluginManager, DatabaseRepository, InstanceRecord]:
    repo = DatabaseRepository(init_db(":memory:"))
    inst = repo.add_instance(
        InstanceCreate(
            id="i1",
            name="Dev",
            url="https://dev.service-now.com",
            username="admin",
            password="pw",
            is_default=True,
        )
    )
    return PluginManager(repo=repo, transport=handler), repo, inst


def _json_transport(rows: list[dict[str, str]]) -> httpx.MockTransport:
    return httpx.MockTransport(lambda req: httpx.Response(200, json={"result": rows}))


def test_install_plugin_inactive_on_instance_not_recorded() -> None:
    mgr, repo, inst = _setup(_json_transport([{"id": "com.snc.itsm", "active": "inactive"}]))
    ok, msg = mgr.install_plugin(inst, "com.snc.itsm")
    assert ok is False
    assert "not active" in msg
    assert repo.list_instance_plugins("i1") == []


def test_install_plugin_active_on_instance_recorded() -> None:
    mgr, repo, inst = _setup(_json_transport([{"id": "com.snc.itsm", "active": "active"}]))
    ok, msg = mgr.install_plugin(inst, "com.snc.itsm")
    assert ok is True
    assert "already active" in msg
    assert [p.plugin_id for p in repo.list_instance_plugins("i1")] == ["com.snc.itsm"]


def test_install_plugin_http_error_returns_failure() -> None:
    mgr, repo, inst = _setup(httpx.MockTransport(lambda req: httpx.Response(500)))
    ok, msg = mgr.install_plugin(inst, "com.snc.itsm")
    assert ok is False
    assert "500" in msg
    assert repo.list_instance_plugins("i1") == []


def test_install_plugin_network_error_returns_failure() -> None:
    def boom(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    mgr, repo, inst = _setup(httpx.MockTransport(boom))
    ok, _ = mgr.install_plugin(inst, "com.snc.itsm")
    assert ok is False
    assert repo.list_instance_plugins("i1") == []


def test_install_plugin_fake_mode_message_says_simulated() -> None:
    mgr, repo, inst = _setup(httpx.MockTransport(lambda req: httpx.Response(500)))
    ok, msg = mgr.install_plugin(inst, "com.snc.itsm", fake_mode=True)
    assert ok is True
    assert "simulated" in msg
    assert len(repo.list_instance_plugins("i1")) == 1


def test_evaluate_plugins_asks_the_instance_and_remembers_active_ones() -> None:
    """Readiness is read from the instance, not only from what the workbench recorded."""

    def by_id(req: httpx.Request) -> httpx.Response:
        query = req.url.params["sysparm_query"]
        rows = [{"id": "com.now_assist_core", "active": "active"}] if "now_assist" in query else []
        return httpx.Response(200, json={"result": rows})

    mgr, repo, inst = _setup(httpx.MockTransport(by_id))
    res = mgr.evaluate_plugins(inst, ["com.now_assist_core", "com.snc.itsm"])
    assert res.installed == ["com.now_assist_core"]
    assert res.missing == ["com.snc.itsm"]
    assert res.reasons["com.snc.itsm"] == "plugin not found or not active"
    assert [p.plugin_id for p in repo.list_instance_plugins("i1")] == ["com.now_assist_core"]


def test_evaluate_plugins_unreachable_instance_says_why() -> None:
    """When the instance cannot answer, the plugin is missing with the reason, never assumed."""
    mgr, _repo, inst = _setup(httpx.MockTransport(lambda req: httpx.Response(503)))
    res = mgr.evaluate_plugins(inst, ["com.snc.incident"])
    assert res.missing == ["com.snc.incident"]
    assert "503" in res.reasons["com.snc.incident"]
