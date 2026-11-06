# tests/test_db_schema.py
# Tests for versioned migrations, connection pragmas, and integrity constraints (ADR-012).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for now_workbench.db.schema and now_workbench.db.session."""

import sqlite3
from pathlib import Path

import pytest

from now_workbench.db import (
    ChatMessageRecord,
    ChatThreadCreate,
    DatabaseRepository,
    InstanceCreate,
    InstanceUpdate,
    db_session,
    init_db,
)
from now_workbench.db.schema import SCHEMA_VERSION, apply_migrations


def _memory_repo() -> DatabaseRepository:
    """Return a repository over a fresh, fully migrated in-memory database."""
    return DatabaseRepository(init_db(":memory:"))


def test_init_db_file_sets_version_and_pragmas(tmp_path: Path) -> None:
    """A new file database is migrated to SCHEMA_VERSION with WAL and FK enforcement."""
    conn = init_db(tmp_path / "fresh.db")
    try:
        assert conn.execute("PRAGMA user_version;").fetchone()[0] == SCHEMA_VERSION
        assert conn.execute("PRAGMA journal_mode;").fetchone()[0] == "wal"
        assert conn.execute("PRAGMA foreign_keys;").fetchone()[0] == 1
        assert conn.execute("PRAGMA busy_timeout;").fetchone()[0] == 5000
    finally:
        conn.close()


def test_apply_migrations_is_idempotent() -> None:
    """Re-running migrations on a current database is a no-op."""
    conn = init_db(":memory:")
    assert apply_migrations(conn) == SCHEMA_VERSION
    conn.close()


def test_apply_migrations_newer_database_raises() -> None:
    """A database written by a newer build is refused rather than corrupted."""
    conn = sqlite3.connect(":memory:")
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1};")
    with pytest.raises(RuntimeError, match="newer"):
        apply_migrations(conn)
    conn.close()


def test_apply_migrations_failure_rolls_back() -> None:
    """A failing migration leaves the database at its previous version."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE instances (id TEXT);")
    with pytest.raises(sqlite3.Error):
        apply_migrations(conn)
    assert conn.execute("PRAGMA user_version;").fetchone()[0] == 0
    assert not conn.in_transaction
    conn.close()


def test_init_db_retires_unversioned_prototype(tmp_path: Path) -> None:
    """A pre-ADR-012 prototype file is moved aside (with sidecars) and a clean schema starts."""
    target = tmp_path / "workbench.db"
    legacy = sqlite3.connect(target)
    legacy.execute("PRAGMA journal_mode = WAL;")
    legacy.execute("CREATE TABLE instances (id TEXT, password TEXT);")
    legacy.execute("INSERT INTO instances VALUES ('old', 'plaintext');")
    legacy.commit()
    conn = init_db(target)
    try:
        backups = list(tmp_path.glob("workbench.db.prototype-*.bak"))
        assert len(backups) == 1
        assert conn.execute("SELECT COUNT(*) FROM instances;").fetchone()[0] == 0
    finally:
        conn.close()
        legacy.close()


def test_init_db_existing_current_database_reuses_schema(tmp_path: Path) -> None:
    """Opening an up-to-date file again keeps its data (no re-migration)."""
    target = tmp_path / "keep.db"
    with db_session(target) as repo:
        repo.add_instance(InstanceCreate(name="Keep", url="https://keep.service-now.com"))
    with db_session(target) as repo:
        assert [i.name for i in repo.list_instances()] == ["Keep"]


def test_add_instance_seals_credentials_at_rest() -> None:
    """Username and password are stored only inside the sealed credentials blob."""
    repo = _memory_repo()
    inst = repo.add_instance(
        InstanceCreate(
            name="Sealed", url="https://s.service-now.com", username="svc", password="P@ss"
        )
    )
    blob = repo.conn.execute("SELECT credentials_sealed FROM instances;").fetchone()[0]
    assert b"P@ss" not in blob and b"svc" not in blob
    assert (inst.username, inst.password) == ("svc", "P@ss")
    repo.close()


def test_add_instance_duplicate_name_raises() -> None:
    """Instance names are unique case-insensitively."""
    repo = _memory_repo()
    repo.add_instance(InstanceCreate(name="Dev", url="https://a.service-now.com"))
    with pytest.raises(ValueError, match="already exists"):
        repo.add_instance(InstanceCreate(name="dev", url="https://b.service-now.com"))
    repo.close()


def test_update_instance_rename_collision_raises() -> None:
    """Renaming onto an existing name is refused."""
    repo = _memory_repo()
    repo.add_instance(InstanceCreate(name="One", url="https://1.service-now.com"))
    two = repo.add_instance(InstanceCreate(name="Two", url="https://2.service-now.com"))
    with pytest.raises(ValueError, match="already exists"):
        repo.update_instance(two.id, InstanceUpdate(name="ONE"))
    repo.close()


def test_single_default_index_rejects_second_default() -> None:
    """The partial unique index guarantees at most one default instance."""
    repo = _memory_repo()
    repo.add_instance(InstanceCreate(name="A", url="https://a.service-now.com", is_default=True))
    repo.add_instance(InstanceCreate(name="B", url="https://b.service-now.com"))
    with pytest.raises(sqlite3.IntegrityError):
        with repo.conn:
            repo.conn.execute("UPDATE instances SET is_default = 1 WHERE name = 'B';")
    repo.close()


def test_update_instance_set_default_moves_flag() -> None:
    """Promoting another instance to default demotes the previous one."""
    repo = _memory_repo()
    a = repo.add_instance(
        InstanceCreate(name="A", url="https://a.service-now.com", is_default=True)
    )
    b = repo.add_instance(InstanceCreate(name="B", url="https://b.service-now.com"))
    repo.update_instance(b.id, InstanceUpdate(is_default=True))
    default, old = repo.get_default_instance(), repo.get_instance(a.id)
    assert default is not None and default.id == b.id
    assert old is not None and old.is_default is False
    repo.close()


def test_delete_instance_cascades_plugins_and_reelects_default() -> None:
    """Deleting the default instance removes its plugins and promotes the next by name."""
    repo = _memory_repo()
    a = repo.add_instance(
        InstanceCreate(name="A", url="https://a.service-now.com", is_default=True)
    )
    b = repo.add_instance(InstanceCreate(name="B", url="https://b.service-now.com"))
    repo.add_instance_plugin(a.id, "com.glide.x", "X")
    assert repo.delete_instance(a.id) is True
    assert repo.conn.execute("SELECT COUNT(*) FROM instance_plugins;").fetchone()[0] == 0
    default = repo.get_default_instance()
    assert default is not None and default.id == b.id
    repo.close()


def test_to_public_withholds_password() -> None:
    """The API view exposes has_password and never the password itself."""
    repo = _memory_repo()
    inst = repo.add_instance(
        InstanceCreate(name="P", url="https://p.service-now.com", password="x")
    )
    public = inst.to_public().model_dump()
    assert "password" not in public
    assert public["has_password"] is True
    repo.close()


def test_delete_thread_cascades_messages() -> None:
    """Messages are removed by the foreign-key cascade, not application code."""
    repo = _memory_repo()
    repo.create_thread(ChatThreadCreate(id="t-1", title="T"))
    repo.add_message(ChatMessageRecord(id="m-1", thread_id="t-1", role="user", content="hi"))
    assert repo.delete_thread("t-1") is True
    assert repo.conn.execute("SELECT COUNT(*) FROM chat_messages;").fetchone()[0] == 0
    assert repo.delete_thread("t-1") is False
    repo.close()


def test_add_message_unknown_thread_rejected() -> None:
    """Foreign keys are enforced: a message cannot reference a missing thread."""
    repo = _memory_repo()
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_message(ChatMessageRecord(id="m-x", thread_id="nope", role="user", content="x"))
    repo.close()


def test_set_secret_empty_value_deletes() -> None:
    """Named secrets are sealed at rest and an empty value removes them."""
    repo = _memory_repo()
    repo.set_secret("svc_token", "tok-123")
    sealed = repo.conn.execute("SELECT sealed FROM secrets WHERE name = 'svc_token';").fetchone()[0]
    assert b"tok-123" not in sealed
    assert repo.get_secret("svc_token") == "tok-123"
    repo.set_secret("svc_token", "")
    assert repo.get_secret("svc_token") == ""
    repo.close()


def test_prepare_file_db_current_database_returns_early(tmp_path: Path) -> None:
    """A second migrator that finds the schema already current does nothing."""
    from now_workbench.db.session import _prepare_file_db

    target = tmp_path / "raced.db"
    init_db(target).close()
    _prepare_file_db(str(target))
    conn = sqlite3.connect(target)
    assert conn.execute("PRAGMA user_version;").fetchone()[0] == SCHEMA_VERSION
    conn.close()


def test_has_instance_plugin_reports_presence() -> None:
    """Plugin lookups distinguish installed from missing plugins."""
    repo = _memory_repo()
    inst = repo.add_instance(InstanceCreate(name="Plug", url="https://p.service-now.com"))
    repo.add_instance_plugin(inst.id, "com.glide.x", "X")
    assert repo.has_instance_plugin(inst.id, "com.glide.x") is True
    assert repo.has_instance_plugin(inst.id, "com.glide.y") is False
    repo.close()


def test_get_workbench_preferences_seeds_key_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """First-use initialization seals WORKBENCH_ANTHROPIC_API_KEY into the secrets table."""
    from now_workbench.config.settings import settings

    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test-env1234")
    repo = _memory_repo()
    prefs = repo.get_workbench_preferences()
    assert prefs.has_anthropic_api_key is True
    assert prefs.anthropic_api_key_masked == "sk-ant-...1234"
    assert repo.get_decrypted_anthropic_api_key() == "sk-ant-test-env1234"
    repo.close()


def test_instances_api_duplicate_name_returns_conflict() -> None:
    """Registering or renaming onto an existing name returns HTTP 409, never a 500."""
    from fastapi.testclient import TestClient

    from now_workbench.api.app import create_app

    client = TestClient(create_app())
    body = {"name": "Conflict", "url": "fake://c.service-now.com", "password": "pw"}
    first = client.post("/api/instances", json=body)
    assert first.status_code == 200
    assert "password" not in first.json()
    assert client.post("/api/instances", json=body).status_code == 409
    other = client.post(
        "/api/instances", json={"name": "Other", "url": "fake://o.service-now.com"}
    ).json()
    renamed = client.put(f"/api/instances/{other['id']}", json={"name": "conflict"})
    assert renamed.status_code == 409
    listed = client.get("/api/instances").json()
    assert all("password" not in inst for inst in listed)


def test_get_data_dir_without_override_uses_settings_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no WORKBENCH_DATA_DIR the import-time settings default applies."""
    from now_workbench.config.settings import settings

    monkeypatch.delenv("WORKBENCH_DATA_DIR")
    assert settings.get_data_dir() == settings.data_dir


def test_apply_migrations_v1_to_v2_keeps_instances_and_drops_release() -> None:
    """Upgrading a v1 registry keeps instances; the stored release column is removed."""
    from now_workbench.db.schema import MIGRATIONS

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(f"BEGIN;\n{MIGRATIONS[0]}\nPRAGMA user_version = 1;\nCOMMIT;")
    conn.execute(
        "INSERT INTO instances (id, name, url, credentials_sealed, release) "
        "VALUES ('v1', 'Legacy', 'https://l.service-now.com', x'01', 'Zurich');"
    )
    conn.commit()
    assert apply_migrations(conn) == SCHEMA_VERSION
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(instances);")}
    assert "release" not in cols
    assert conn.execute("SELECT name FROM instances;").fetchone()["name"] == "Legacy"
    tables = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';")}
    assert {"instance_profiles", "instance_nodes"} <= tables
    conn.close()


def test_apply_migrations_v2_to_v3_adds_purpose_and_renames_reported_fields() -> None:
    """v3 defaults existing instances to 'demo' and keeps reported profile values."""
    from now_workbench.db.schema import MIGRATIONS

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        f"BEGIN;\n{MIGRATIONS[0]}\n{MIGRATIONS[1]}\nPRAGMA user_version = 2;\nCOMMIT;"
    )
    conn.execute(
        "INSERT INTO instances (id, name, url, credentials_sealed) "
        "VALUES ('v2', 'Demo', 'https://d.service-now.com', x'01');"
    )
    conn.execute(
        "INSERT INTO instance_profiles (instance_id, environment, is_production) "
        "VALUES ('v2', 'prod', 1);"
    )
    conn.commit()
    assert apply_migrations(conn) == SCHEMA_VERSION
    assert conn.execute("SELECT purpose FROM instances;").fetchone()["purpose"] == "demo"
    row = conn.execute(
        "SELECT instance_type, production_property FROM instance_profiles;"
    ).fetchone()
    assert (row["instance_type"], row["production_property"]) == ("prod", 1)
    conn.close()


def test_apply_migrations_v3_to_v4_strips_default_release_preference() -> None:
    """Stored preferences lose the removed default_sn_release key and keep the rest."""
    from now_workbench.db.schema import MIGRATIONS

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "BEGIN;\n" + "\n".join(MIGRATIONS[:3]) + "\nPRAGMA user_version = 3;\nCOMMIT;"
    )
    conn.execute(
        "INSERT INTO workbench_preferences (id, payload) VALUES "
        '(1, \'{"default_sn_release": "Zurich", "narrative_tone": "executive"}\');'
    )
    conn.commit()
    assert apply_migrations(conn) == SCHEMA_VERSION
    payload = conn.execute("SELECT payload FROM workbench_preferences;").fetchone()["payload"]
    assert "default_sn_release" not in payload
    assert "executive" in payload
    conn.close()
