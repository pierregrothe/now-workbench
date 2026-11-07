# tests/test_ownership.py
# Per-user ownership: the ambient owner, fail-closed queries, isolation and the v8 migration.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for ADR-018 owner scoping."""

import asyncio
import sqlite3
from contextvars import Context

import pytest
from access_kit import as_user, multi_user_client

from now_workbench.domains.conversations.models import ChatThreadCreate
from now_workbench.domains.conversations.repository import ThreadRepository
from now_workbench.domains.identity.models import Role
from now_workbench.domains.identity.owner import operator_owner
from now_workbench.domains.identity.repository import UserRepository
from now_workbench.domains.instances.models import InstanceCreate
from now_workbench.domains.instances.repository import InstanceRepository
from now_workbench.domains.settings.repository import PreferencesRepository
from now_workbench.interfaces.ai.tools.base import run_async
from now_workbench.platform.db.schema import MIGRATIONS, SCHEMA_VERSION, apply_migrations
from now_workbench.platform.db.session import init_db
from now_workbench.platform.owner import LOCAL_EMAIL, NoOwnerError, current_owner, owner_scope

ADMIN, ANA, BEN = "admin@example.com", "ana@example.com", "ben@example.com"


def _instance(name: str, inst_id: str | None = None) -> InstanceCreate:
    return InstanceCreate(
        id=inst_id, name=name, url="fake://x.service-now.com", username="u", password="p"
    )


def test_current_owner_outside_any_scope_raises() -> None:
    """A query with no owner fails instead of returning everyone's rows."""
    with pytest.raises(NoOwnerError):
        Context().run(current_owner)


def test_list_instances_shows_only_the_owners_rows() -> None:
    """Two people with the same instance name each see only their own."""
    conn = init_db(":memory:")
    instance_repo = InstanceRepository(conn)
    with owner_scope(ANA):
        instance_repo.add_instance(_instance("Dev", "inst-ana"))
    with owner_scope(BEN):
        instance_repo.add_instance(_instance("Dev", "inst-ben"))
        assert [i.id for i in instance_repo.list_instances()] == ["inst-ben"]
        assert instance_repo.get_instance("inst-ana") is None
        assert instance_repo.get_default_instance() is not None
        assert instance_repo.delete_instance("inst-ana") is False
    with owner_scope(ANA):
        assert [i.id for i in instance_repo.list_instances()] == ["inst-ana"]
    conn.close()


def test_add_instance_with_another_owners_id_gets_a_new_id() -> None:
    """Reusing someone else's id never overwrites their instance."""
    conn = init_db(":memory:")
    instance_repo = InstanceRepository(conn)
    with owner_scope(ANA):
        instance_repo.add_instance(_instance("Ana", "shared-id"))
    with owner_scope(BEN):
        created = instance_repo.add_instance(_instance("Ben", "shared-id"))
        assert created.id != "shared-id"
    with owner_scope(ANA):
        mine = instance_repo.get_instance("shared-id")
        assert mine is not None
        assert mine.name == "Ana"
    conn.close()


def test_threads_are_private_and_ids_cannot_be_hijacked() -> None:
    """Another owner can neither read, rename, delete nor write into a thread."""
    conn = init_db(":memory:")
    thread_repo = ThreadRepository(conn)
    with owner_scope(ANA):
        thread_repo.create_thread(ChatThreadCreate(id="t-1", title="Ana's"))
    with owner_scope(BEN):
        assert thread_repo.list_threads() == []
        assert thread_repo.get_thread("t-1") is None
        assert thread_repo.list_messages("t-1") == []
        assert thread_repo.delete_thread("t-1") is False
        hijack = thread_repo.create_thread(ChatThreadCreate(id="t-1", title="Ben's"))
        assert hijack.id != "t-1"
    with owner_scope(ANA):
        thread = thread_repo.get_thread("t-1")
        assert thread is not None
        assert thread.title == "Ana's"
    conn.close()


def test_preferences_are_per_user() -> None:
    """One person's settings do not change another's."""
    from now_workbench.domains.settings.models import WorkbenchPreferencesUpdate

    conn = init_db(":memory:")
    pref_repo = PreferencesRepository(conn)
    with owner_scope(ANA):
        pref_repo.update_workbench_preferences(
            WorkbenchPreferencesUpdate(narrative_tone="technical")
        )
    with owner_scope(BEN):
        assert pref_repo.get_workbench_preferences().narrative_tone == "executive"
    conn.close()


def test_operator_owner_claims_orphans_for_the_first_admin() -> None:
    """Rows created before any admin go to the first admin (or the local operator)."""
    conn = init_db(":memory:")
    instance_repo = InstanceRepository(conn)
    with owner_scope(""):
        instance_repo.add_instance(_instance("Early", "inst-early"))
    assert operator_owner(conn, local_mode=False) == ""
    UserRepository(conn).put_user(ADMIN, frozenset(Role), added_by="test")
    assert operator_owner(conn, local_mode=False) == ADMIN
    with owner_scope(ADMIN):
        assert [i.id for i in instance_repo.list_instances()] == ["inst-early"]
    conn.close()


def test_operator_owner_in_local_mode_is_the_local_operator() -> None:
    """Without Access and without admins the local operator owns start-up data."""
    conn = init_db(":memory:")
    assert operator_owner(conn, local_mode=True) == LOCAL_EMAIL
    conn.close()


def test_run_async_keeps_the_owner_in_the_worker_thread() -> None:
    """Tool code bridged to a thread still runs as the signed-in owner."""

    async def who() -> str:
        return current_owner()

    async def inside_loop() -> str:
        return run_async(who())

    with owner_scope(ANA):
        assert asyncio.run(inside_loop()) == ANA


def test_apply_migrations_v7_to_v8_gives_rows_to_the_first_admin() -> None:
    """Existing instances, threads and preferences move to the earliest administrator."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    script = "\n".join(MIGRATIONS[:7])
    conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = 7;\nCOMMIT;")
    conn.executescript(
        f"""
        INSERT INTO users (email, is_admin, is_consultant) VALUES ('{ADMIN}', 1, 1);
        INSERT INTO instances (id, name, url, credentials_sealed, is_default)
            VALUES ('i1', 'Dev', 'fake://d', x'00', 1);
        INSERT INTO instance_plugins (instance_id, plugin_id, plugin_name)
            VALUES ('i1', 'p', 'P');
        INSERT INTO chat_threads (id, title) VALUES ('t1', 'Hello');
        INSERT INTO workbench_preferences (id, payload) VALUES (1, '{{"narrative_tone": "x"}}');
        """
    )
    conn.execute("PRAGMA foreign_keys = ON;")
    assert apply_migrations(conn) == SCHEMA_VERSION
    assert conn.execute("SELECT owner_email FROM instances;").fetchone()[0] == ADMIN
    assert conn.execute("SELECT owner_email FROM chat_threads;").fetchone()[0] == ADMIN
    assert conn.execute("SELECT email FROM user_preferences;").fetchone()[0] == ADMIN
    assert conn.execute("SELECT COUNT(*) FROM instance_plugins;").fetchone()[0] == 1
    assert conn.execute("PRAGMA foreign_keys;").fetchone()[0] == 1
    conn.close()


def test_threads_api_isolates_two_signed_in_people() -> None:
    """Over HTTP, a consultant cannot open the admin's conversation."""
    with multi_user_client(ADMIN, (ANA,)) as client:
        created = client.post(
            "/api/threads", json={"title": "Admin only"}, headers=as_user(ADMIN)
        ).json()
        ana_threads = client.get("/api/threads", headers=as_user(ANA)).json()
        assert created["id"] not in {t["id"] for t in ana_threads}
        res = client.get(f"/api/threads/{created['id']}", headers=as_user(ANA))
        assert res.status_code == 404
