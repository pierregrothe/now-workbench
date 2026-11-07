# tests/test_conversational_control.py
# Otto knows its audience, moves the interface, confirms in words; the Actions screen runs it all.
# Author: Pierre Grothe
# Date: 2026-11-07
"""ADR-026: audience, role-filtered tools, navigation, account tools, confirmation, actions."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from access_kit import as_user, multi_user_client
from fastapi.testclient import TestClient

from now_workbench.domains.conversations import ChatMessageRecord, ThreadRepository
from now_workbench.domains.groups import GroupKind, GroupRepository, MemberRole
from now_workbench.domains.identity import AuthUser, Role, actor_scope
from now_workbench.interfaces.ai.agent import _assemble, run_agent
from now_workbench.interfaces.ai.audience import audience_for
from now_workbench.interfaces.ai.conversation import Question, build_request
from now_workbench.interfaces.ai.tools import execute_tool, tool_definitions
from now_workbench.interfaces.ai.tools.base import ToolContext, ToolResult
from now_workbench.interfaces.api.app import create_app
from now_workbench.platform.db.session import db_session
from now_workbench.platform.owner import LOCAL_EMAIL

ADMIN, ANA = "admin@example.com", "ana@example.com"


def _user(email: str, admin: bool = False, real: str | None = None) -> AuthUser:
    roles = frozenset(Role) if admin else frozenset({Role.SOLUTION_CONSULTANT})
    return AuthUser(email=email, roles=roles, mode="cloudflare", real_email=real)


def _run(
    tool: str,
    args: dict[str, Any] | None = None,
    thread: str = "",
    user: AuthUser | None = None,
    confirmed: bool = False,
) -> ToolResult:
    with db_session() as conn:
        ctx = ToolContext(conn=conn, user=user or _user(LOCAL_EMAIL, admin=True), thread_id=thread)
        return execute_tool(ctx, tool, args or {}, confirmed)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


# --- audience ------------------------------------------------------------------------------


def test_audience_for_describes_roles_groups_and_view_as() -> None:
    """Otto is told who it helps, which groups they lead or belong to, and who views as them."""
    with db_session() as conn:
        assert audience_for(conn, None).description == ""
        groups = GroupRepository(conn)
        led = groups.create_group("EMEA", GroupKind.REGION, "", ADMIN)
        member = groups.create_group("APJ", GroupKind.REGION, "", ADMIN)
        groups.create_group("NA", GroupKind.REGION, "", ADMIN)
        groups.put_group_member(led.id, ANA, MemberRole.ADMIN, decided_by=ADMIN)
        groups.put_group_member(member.id, ANA, MemberRole.MEMBER, decided_by=ADMIN)
        groups.request_to_join(groups.list_groups(ANA)[-1].id, ANA)
        ana = audience_for(conn, _user(ANA, real=ADMIN))
        boss = audience_for(conn, _user(ADMIN, admin=True))
    assert not ana.admin and "administers EMEA" in ana.description
    assert "member of APJ" in ana.description and "asked to join" in ana.description
    assert "viewing the workbench as this person" in ana.description
    assert "may not manage the team" in ana.description
    assert boss.admin and "not in any group yet" in boss.description
    assert "manage the team" in boss.description


def test_build_request_adds_the_audience_and_filters_admin_tools() -> None:
    """The audience follows the cached prefix; consultants are not offered admin tools."""
    from now_workbench.interfaces.ai.audience import Audience

    req = build_request("m", [], 100_000, Audience(description="Who: Ana", admin=False))
    assert req["system"][0]["cache_control"] and req["system"][1] == {
        "type": "text",
        "text": "Who: Ana",
    }
    names = {t["name"] for t in req["tools"]}
    assert "list_team" not in names and "list_groups" in names
    assert "list_team" in {t["name"] for t in tool_definitions()}
    assert len(build_request("m", [], 100_000)["system"]) == 1


def test_run_agent_tells_claude_who_is_signed_in() -> None:
    """Inside a request, the agent sends the signed-in person's description."""

    class _Messages:
        calls: list[dict[str, Any]] = []

        def create(self, **kw: Any) -> Any:
            self.calls.append(kw)
            block = type("B", (), {"type": "text", "text": "Hi."})()
            return type("R", (), {"content": [block], "stop_reason": "end_turn", "usage": None})()

    client = type("C", (), {"messages": _Messages()})()
    with db_session() as conn, actor_scope(_user(ANA)):
        run_agent(Question("hello", thread_id="t-1"), conn, client, "m")
    assert ANA in client.messages.calls[0]["system"][1]["text"]


# --- navigation ------------------------------------------------------------------------------


def test_open_screen_sends_interface_commands() -> None:
    """Screens, Settings sections and pre-filled actions become commands; bad targets refuse."""
    home = _run("open_screen", {"screen": "home"})
    assert home.ui == [{"type": "navigate", "tab": "home"}]
    groups = _run("open_screen", {"screen": "admin", "section": "groups"})
    assert groups.ui[0]["section"] == "groups" and "Settings > groups" in groups.summary
    action = _run(
        "open_screen", {"screen": "actions", "action": "list_instances", "args": {"detailed": True}}
    )
    assert action.ui[0] == {
        "type": "navigate",
        "tab": "actions",
        "action": "list_instances",
        "args": {"detailed": True},
    }
    assert not _run("open_screen", {"screen": "moon"}).ok
    assert not _run("open_screen", {"screen": "home", "section": "groups"}).ok
    assert not _run("open_screen", {"screen": "actions", "action": "show"}).ok
    assert not _run("open_screen", {"screen": "actions", "action": "list_team"}, user=_user(ANA)).ok


def test_assemble_collects_interface_commands_of_successful_tools() -> None:
    """Only commands of tools that succeeded reach the interface."""
    ok = ToolResult(summary="ok", ui=[{"type": "navigate", "tab": "home"}])
    failed = ToolResult(summary="no", ok=False, ui=[{"type": "navigate", "tab": "admin"}])
    assert _assemble("Done.", [ok, failed]).ui == [{"type": "navigate", "tab": "home"}]


# --- account tools ---------------------------------------------------------------------------


def test_profile_tools_show_and_change_the_profile(client: TestClient) -> None:
    """The person renames themselves and picks a built-in avatar through Otto."""
    assert _run("update_profile", {"display_name": "Pierre", "avatar_preset": "sun"}).ok
    shown = _run("show_profile")
    assert shown.tiles[0].props["rows"][0] == ["Name", "Pierre"]
    assert shown.tiles[0].props["rows"][3] == ["Avatar", "sun"]
    assert not _run("update_profile").ok
    assert "Unknown avatar" in _run("update_profile", {"avatar_preset": "not-an-avatar"}).summary


def test_conversation_tools_rename_archive_and_delete(client: TestClient) -> None:
    """Conversations are found by title, id or as 'this one'."""
    first = client.post("/api/threads", json={"title": "Quarterly prep"}).json()["id"]
    client.post("/api/threads", json={"title": "Quarterly review"})
    listed = _run("list_conversations", thread=first)
    assert any("(this one)" in r[0] for r in listed.tiles[0].props["rows"])
    assert not _run("rename_conversation", {"title": "x", "conversation": "Quarterly"}).ok
    assert _run("rename_conversation", {"title": "Q3 prep"}, thread=first).ok
    assert not _run("rename_conversation", {"title": "x"}).ok  # no conversation at all
    assert "Archived" in _run("archive_conversation", {"conversation": "Q3 prep"}).summary
    assert (
        "Restored"
        in _run("archive_conversation", {"conversation": first, "archived": False}).summary
    )
    assert _run("delete_conversation", {"conversation": "Q3 prep"}).pending
    assert _run("delete_conversation", {"conversation": "Q3 prep"}, confirmed=True).ok


def test_attachment_tools_list_and_remove_unsent_files(client: TestClient) -> None:
    """Unsent files can be removed by name; sent ones are refused."""
    thread = client.post("/api/threads", json={"title": "Files"}).json()["id"]
    client.post(
        f"/api/threads/{thread}/attachments", params={"filename": "notes.txt"}, content=b"hello"
    )
    listed = _run("list_attachments", thread=thread)
    assert listed.tiles[0].props["rows"][0][0] == "notes.txt"
    assert not _run("remove_attachment", {"file": "other.txt"}, thread=thread).ok
    assert _run("remove_attachment", {"file": "notes.txt"}, thread=thread).ok
    assert _run("list_attachments", thread=thread).data["attachments"] == []


# --- conversational confirmation ----------------------------------------------------------------


def _proposal_then_answer(client: TestClient, answered: bool = True) -> str:
    thread = client.post("/api/threads", json={"title": "Confirm"}).json()["id"]
    pending = _run("delete_conversation", {"conversation": "Doomed"})
    client.post("/api/threads", json={"title": "Doomed"})
    with db_session() as conn:
        repo = ThreadRepository(conn)
        widget = {"tiles": [t.model_dump() for t in pending.tiles]}
        repo.add_message(
            ChatMessageRecord(
                id="a1", thread_id=thread, role="assistant", content="Sure?", widget_data=widget
            )
        )
        if answered:
            repo.add_message(
                ChatMessageRecord(id="u1", thread_id=thread, role="user", content="yes")
            )
    return str(thread)


def test_confirm_action_runs_a_proposal_the_person_agreed_to(client: TestClient) -> None:
    """The proposal in Otto's last reply runs once the person answered."""
    thread = _proposal_then_answer(client)
    assert not _run("confirm_action", {"tool": "delete_group"}, thread=thread).ok
    done = _run("confirm_action", thread=thread)
    assert done.ok and "Deleted 'Doomed'" in done.summary


def test_confirm_action_refuses_without_an_answer_or_a_conversation(client: TestClient) -> None:
    """No conversation, no reply yet, or no proposal: nothing runs."""
    assert "no conversation" in _run("confirm_action").summary
    thread = _proposal_then_answer(client, answered=False)
    assert "not answered" in _run("confirm_action", thread=thread).summary
    with db_session() as conn:
        ThreadRepository(conn).add_message(
            ChatMessageRecord(id="u2", thread_id=thread, role="user", content="ok")
        )
        ThreadRepository(conn).add_message(
            ChatMessageRecord(id="a2", thread_id=thread, role="assistant", content="Done.")
        )
        ThreadRepository(conn).add_message(
            ChatMessageRecord(id="u3", thread_id=thread, role="user", content="again")
        )
    assert "Nothing to confirm" in _run("confirm_action", thread=thread).summary


# --- actions API ------------------------------------------------------------------------------


@pytest.fixture
def team(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    bundles = tmp_path / "bundles"
    (bundles / "starter").mkdir(parents=True)
    (bundles / "starter" / "manifest.json").write_text(
        json.dumps({"id": "starter", "name": "S"}), encoding="utf-8"
    )
    monkeypatch.setenv("WORKBENCH_BUNDLES_DIR", str(bundles))
    with multi_user_client(ADMIN, (ANA,)) as c:
        yield c


def test_list_actions_is_the_registry_filtered_for_the_person(team: TestClient) -> None:
    """Otto-only tools are hidden; administrator actions only for administrators."""
    admin = {a["name"] for a in team.get("/api/actions", headers=as_user(ADMIN)).json()}
    ana = {a["name"] for a in team.get("/api/actions", headers=as_user(ANA)).json()}
    assert {"list_team", "list_instances"} <= admin and "show" not in admin
    assert "list_team" not in ana and "list_instances" in ana and "confirm_action" not in ana


def test_run_action_runs_as_the_person_with_confirmation(team: TestClient) -> None:
    """Actions run with the person's rights; changes that need it are confirmed in a second call."""
    ran = team.post("/api/actions/list_groups", json={}, headers=as_user(ANA)).json()
    assert ran["ok"] and ran["tiles"][0]["type"] == "data-table"
    assert team.post("/api/actions/list_team", json={}, headers=as_user(ANA)).status_code == 404
    assert team.post("/api/actions/show", json={}, headers=as_user(ADMIN)).status_code == 404
    made = team.post(
        "/api/actions/create_group",
        json={"args": {"name": "EMEA", "kind": "region"}},
        headers=as_user(ADMIN),
    )
    assert made.json()["ok"]
    review = team.post(
        "/api/actions/delete_group", json={"args": {"group": "EMEA"}}, headers=as_user(ADMIN)
    )
    assert review.json()["pending"]
    done = team.post(
        "/api/actions/delete_group",
        json={"args": {"group": "EMEA"}, "confirmed": True},
        headers=as_user(ADMIN),
    )
    assert done.json()["ok"] and "Deleted group" in done.json()["summary"]


async def test_runner_passes_the_conversation_to_its_tools() -> None:
    """The async runner (used by run_agent outside an event loop) keeps the conversation id."""
    from now_workbench.interfaces.ai.agent import ClaudeAgentRunner

    class _Messages:
        async def create(self, **kw: Any) -> Any:
            block = type("B", (), {"type": "text", "text": "Hi."})()
            return type("R", (), {"content": [block], "stop_reason": "end_turn", "usage": None})()

    client = type("C", (), {"messages": _Messages()})()
    with db_session() as conn:
        runner = ClaudeAgentRunner(client, "m", conn)
        await runner.run(Question("hello", thread_id="t-9"))
    assert runner.ctx.thread_id == "t-9"
