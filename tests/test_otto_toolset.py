# tests/test_otto_toolset.py
# Otto's sharing and admin tools act as the signed-in person; `show` presents catalog tiles.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests for the ADR-025 tool set: same rules as the API, visual tiles from a catalog."""

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from access_kit import multi_user_client
from fastapi.testclient import TestClient

from now_workbench.domains.identity import AuthUser, NoActorError, Role, actor_scope, current_actor
from now_workbench.domains.instances import InstanceCreate, InstanceRepository
from now_workbench.domains.seed import SeedRepository
from now_workbench.domains.seed.models import SeedOperationRecord, SeedRecordItem
from now_workbench.interfaces.ai.agent import _assemble
from now_workbench.interfaces.ai.tools import execute_tool
from now_workbench.interfaces.ai.tools.base import ToolContext, ToolResult
from now_workbench.platform.db.session import db_session
from now_workbench.platform.owner import owner_scope

ADMIN, ANA, BEN = "admin@example.com", "ana@example.com", "ben@example.com"


def _user(email: str) -> AuthUser:
    roles = frozenset(Role) if email == ADMIN else frozenset({Role.SOLUTION_CONSULTANT})
    return AuthUser(email=email, roles=roles, mode="cloudflare")


@pytest.fixture
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """The admin owns the 'starter' bundle (with a runbook); Ana and Ben are consultants."""
    bundles = tmp_path / "bundles"
    starter = bundles / "starter"
    (starter / "seed").mkdir(parents=True)
    (starter / "manifest.json").write_text(
        json.dumps({"id": "starter", "name": "Starter", "description": "d"}), encoding="utf-8"
    )
    monkeypatch.setenv("WORKBENCH_BUNDLES_DIR", str(bundles))
    with multi_user_client(ADMIN, (ANA, BEN)) as client:
        yield client


def _run(
    email: str, tool: str, args: dict[str, Any] | None = None, confirmed: bool = True
) -> ToolResult:
    """Run a tool as ``email`` the way the agent does (inside the person's owner scope)."""
    with db_session() as conn, owner_scope(email):
        return execute_tool(ToolContext(conn=conn, user=_user(email)), tool, args or {}, confirmed)


def _group(name: str = "EMEA") -> str:
    res = _run(ADMIN, "create_group", {"name": name, "kind": "region"})
    assert res.ok, res.summary
    return str(res.data["id"])


# --- actor -------------------------------------------------------------------------------


def test_current_actor_outside_a_request_fails_closed() -> None:
    """No signed-in person, no rule can be applied."""
    with pytest.raises(NoActorError):
        current_actor()


def test_tool_context_actor_falls_back_to_the_request_actor(app: TestClient) -> None:
    """Without an explicit user the context acts for the request's person."""
    with db_session() as conn, actor_scope(_user(ANA)):
        assert ToolContext(conn=conn).actor().email == ANA


# --- sharing tools -------------------------------------------------------------------------


def test_group_tools_follow_the_same_rules_as_the_api(app: TestClient) -> None:
    """Admins create groups; members ask to join; group admins manage members."""
    assert not _run(ANA, "create_group", {"name": "Nope", "kind": "region"}).ok
    group = _group()
    _group("EMEA North")
    listed = _run(ANA, "list_groups")
    assert listed.ok and listed.tiles[0].props["columns"][0] == "Group"
    assert "Asked to join 'EMEA'" in _run(ANA, "join_group", {"group": "emea"}).summary
    assert not _run(ANA, "join_group", {"group": "EM"}).ok  # two groups match
    assert not _run(ANA, "list_group_members", {"group": group}).ok  # not a group admin
    added = _run(ADMIN, "set_group_member", {"group": "EMEA", "email": BEN, "role": "admin"})
    assert added.ok and "admin" in added.summary
    members = _run(BEN, "list_group_members", {"group": "North"})
    assert not members.ok  # Ben administers EMEA, not EMEA North
    members = _run(BEN, "list_group_members", {"group": group})
    assert {r[0] for r in members.tiles[0].props["rows"]} >= {ANA, BEN}
    assert _run(BEN, "remove_group_member", {"group": group, "email": ANA}).ok
    assert _run(ADMIN, "delete_group", {"group": group}).ok


def test_destructive_sharing_tools_ask_for_confirmation_first(app: TestClient) -> None:
    """Deleting, removing, deciding and withdrawing return a plan to confirm."""
    _group()
    for tool, args in (
        ("delete_group", {"group": "EMEA"}),
        ("set_group_member", {"group": "EMEA", "email": ANA}),
        ("remove_group_member", {"group": "EMEA", "email": ANA}),
        ("withdraw_share", {"bundle_id": "starter", "share_id": "s1"}),
        ("decide_share", {"share_id": "s1", "approve": False}),
        ("set_team_roles", {"email": ANA, "admin": True}),
        ("remove_team_member", {"email": ANA}),
        ("set_limits", {"max_files": 5}),
    ):
        res = _run(ADMIN, tool, args, confirmed=False)
        assert res.pending, tool


def test_version_and_share_tools_take_a_bundle_through_approval(app: TestClient) -> None:
    """The owner saves a version and shares it with a group they administer."""
    assert _run(ADMIN, "save_version", {"bundle_id": "starter", "note": "first"}).ok
    versions = _run(ADMIN, "list_versions", {"bundle_id": "starter"})
    # Newest first; shipped bundles already have version 1 from startup.
    assert versions.tiles[0].props["rows"][0][1] == "first"
    group = _group()
    _run(ADMIN, "set_group_member", {"group": group, "email": BEN, "role": "admin"})
    # The bundle is the admin's, so Ben (not the owner) is told it does not exist.
    assert not _run(BEN, "list_shares", {"bundle_id": "starter"}).ok
    shared = _run(
        ADMIN, "share_bundle", {"bundle_id": "starter", "target": "group", "group": "EMEA"}
    )
    assert shared.ok and "approved" in shared.summary
    shares = _run(ADMIN, "list_shares", {"bundle_id": "starter"})
    share_id = shares.data["shares"][0]["id"]
    assert _run(ADMIN, "withdraw_share", {"bundle_id": "starter", "share_id": share_id}).ok


def test_approval_tools_let_a_group_admin_decide(app: TestClient) -> None:
    """A pending share shows in the approver's inbox and can be decided there."""
    with db_session() as conn, owner_scope(ADMIN):
        from now_workbench.domains import sharing

        sharing.save_new_version(conn, _user(ADMIN), "starter", "")
        pending = sharing.request_share(conn, _user(ADMIN), "starter", sharing.ShareTarget.GLOBAL)
    # An admin's own global share is approved at once; make a pending one to decide.
    with db_session() as conn:
        conn.execute("UPDATE artifact_shares SET status = 'pending' WHERE id = ?;", (pending.id,))
        conn.commit()
    inbox = _run(ADMIN, "approval_inbox")
    assert inbox.ok and inbox.layout == "2-col"
    assert inbox.tiles[0].props["rows"][0][0] == pending.id
    assert not _run(ANA, "decide_share", {"share_id": pending.id, "approve": True}).ok
    decided = _run(ADMIN, "decide_share", {"share_id": pending.id, "approve": False})
    assert decided.ok and "rejected" in decided.summary


# --- admin tools -------------------------------------------------------------------------


def test_team_and_limit_tools_are_for_administrators_only(app: TestClient) -> None:
    """Consultants are refused; administrators manage the team and the limits."""
    assert not _run(ANA, "list_team").ok
    assert _run(ADMIN, "list_team").tiles[0].props["columns"] == ["Email", "Roles", "Added by"]
    assert _run(ADMIN, "set_team_roles", {"email": BEN, "admin": True}).ok
    assert not _run(ADMIN, "set_team_roles", {"email": BEN}).ok  # no role at all
    assert _run(ADMIN, "remove_team_member", {"email": BEN}).ok
    assert _run(ANA, "show_limits").data["max_files"] >= 1
    assert not _run(ANA, "set_limits", {"max_files": 3}).ok
    assert _run(ADMIN, "set_limits", {"max_files": 3}).data["max_files"] == 3


# --- show --------------------------------------------------------------------------------


def _add_instance(conn: sqlite3.Connection) -> None:
    InstanceRepository(conn).add_instance(
        InstanceCreate(id="alpha", name="Alpha", url="https://alpha.service-now.com")
    )


def test_show_generic_tiles_carry_otto_content_and_follow_ups(app: TestClient) -> None:
    """Generic tiles are validated, typed for the renderer and carry clickable prompts."""
    tiles = [
        {
            "kind": "text",
            "title": "Why",
            "body": "Because.",
            "actions": [{"label": "More", "prompt": "Tell me more"}],
        },
        {"kind": "table", "columns": ["A"], "rows": [["1"]]},
        {"kind": "kpis", "items": [{"label": "Instances", "value": "3", "tone": "good"}]},
        {"kind": "steps", "items": [{"label": "Seed", "status": "done"}]},
        {
            "kind": "comparison",
            "columns": [{"heading": "A", "points": ["x"]}, {"heading": "B", "points": ["y"]}],
        },
        {"kind": "callout", "body": "Careful", "tone": "warning", "span": 3},
    ]
    res = _run(ANA, "show", {"tiles": tiles})
    assert res.ok and res.shown and res.layout == "auto"
    assert [t.type for t in res.tiles] == [
        "rich-text",
        "data-table",
        "kpis",
        "steps",
        "comparison",
        "callout",
    ]
    assert res.tiles[0].props["actions"] == [
        {"id": "ask", "label": "More", "prompt": "Tell me more"}
    ]
    assert res.tiles[0].title == "Why"
    assert [t.span for t in res.tiles] == [None, None, None, None, None, 3]
    assert "span" not in res.tiles[-1].props


def test_show_entity_tiles_load_the_record_for_the_signed_in_person(app: TestClient) -> None:
    """Entity tiles come from the data; a record the person cannot see is reported, not shown."""
    with db_session() as conn, owner_scope(ADMIN):
        _add_instance(conn)
        SeedRepository(conn).record_seed_operation(
            SeedOperationRecord(
                id="op-1",
                bundle_id="starter",
                instance_id="alpha",
                created_records=[SeedRecordItem(table="incident", sys_id="abc")],
            )
        )
    res = _run(
        ADMIN,
        "show",
        {
            "tiles": [
                {"kind": "instance", "instance": "Alpha"},
                {"kind": "bundle", "bundle_id": "starter"},
                {"kind": "seed_run", "operation_id": "op-1"},
                {"kind": "diagnostics"},
                {"kind": "runbook", "bundle_id": "starter"},
            ],
            "layout": "1-col",
        },
    )
    types = [t.type for t in res.tiles]
    assert res.ok and res.layout == "1-col" and "runbook" in res.summary
    assert types[0] == "instance" and res.tiles[0].props["name"] == "Alpha"
    assert "password" not in res.tiles[0].props
    assert res.tiles[2].props["rows"] == [["incident", "abc"]]
    assert types[-1] == "diagnostics"
    hidden = _run(ANA, "show", {"tiles": [{"kind": "bundle", "bundle_id": "starter"}]})
    assert not hidden.ok and "Not shown" in hidden.summary
    missing = _run(ADMIN, "show", {"tiles": [{"kind": "seed_run", "operation_id": "nope"}]})
    assert not missing.ok


def test_show_rejects_invalid_or_empty_requests(app: TestClient) -> None:
    """Otto gets the validation error to correct; nothing half-valid is drawn."""
    assert "Invalid tiles" in _run(ANA, "show", {"tiles": [{"kind": "chart"}]}).summary
    assert _run(ANA, "show", {"tiles": []}).summary == "No tiles given."


def test_assemble_shows_only_otto_tiles_once_it_called_show() -> None:
    """Curated tiles replace tool tiles; pending confirmations always stay visible."""
    from now_workbench.interfaces.ai.tools.base import table_tile, text_tile

    tool = ToolResult(summary="listed", tiles=[table_tile("t1", "List", ["A"], [["1"]])])
    pending = ToolResult(summary="confirm?", pending=True, tiles=[text_tile("t2", "Confirm", "x")])
    shown = ToolResult(summary="shown", shown=True, tiles=[text_tile("t3", "Aid", "y")])
    reply = _assemble("Done.", [tool, pending, shown])
    assert [t.id for t in reply.tiles] == ["t2", "t3"]
    plain = _assemble("Done.", [tool])
    assert [t.id for t in plain.tiles] == ["t1"]
    laid_out = shown.model_copy(update={"layout": "3-col"})
    assert _assemble("Done.", [laid_out]).layout == "3-col"  # Otto's layout is kept
