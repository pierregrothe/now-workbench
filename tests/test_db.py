"""Tests for SQLite database repository and instance registry."""

from pathlib import Path

from now_workbench.auth.owner import owner_scope
from now_workbench.db import (
    ChatMessageRecord,
    ChatThreadCreate,
    DatabaseRepository,
    InstanceCreate,
    InstanceUpdate,
    TemplateRecord,
    db_session,
    init_db,
)


def test_instance_registry_lifecycle() -> None:
    """Test registering, retrieving, and setting default instances in SQLite."""
    conn = init_db(":memory:")
    repo = DatabaseRepository(conn)

    # Initially empty
    assert repo.list_instances() == []
    assert repo.get_default_instance() is None

    # Register first instance
    inst1 = repo.add_instance(
        InstanceCreate(
            id="demo-trial",
            name="Demo Trial Zurich",
            url="https://demoalectriallwfau164179.service-now.com",
            username="admin",
            password="secret_password",
            is_default=True,
        )
    )
    assert inst1.id == "demo-trial"
    assert inst1.is_default is True

    # Register second instance
    inst2 = repo.add_instance(
        InstanceCreate(
            id="acme-sandbox",
            name="Acme Corp Sandbox",
            url="https://acmesandbox.service-now.com",
            is_default=False,
        )
    )
    assert inst2.id == "acme-sandbox"

    # Default is inst1
    current_default = repo.get_default_instance()
    assert current_default is not None
    assert current_default.id == "demo-trial"

    # Switch default to inst2
    repo.set_default_instance("acme-sandbox")
    new_default = repo.get_default_instance()
    assert new_default is not None
    assert new_default.id == "acme-sandbox"

    # Status update
    repo.update_instance_status("acme-sandbox", "online")
    updated = repo.get_instance("acme-sandbox")
    assert updated is not None
    assert updated.status == "online"
    assert updated.last_checked is not None

    # Query by name
    by_name = repo.get_instance("Acme Corp Sandbox")
    assert by_name is not None
    assert by_name.id == "acme-sandbox"

    # Update instance (rename and update auth)
    from now_workbench.db.models import InstanceUpdate

    up_rec = repo.update_instance(
        "acme-sandbox",
        InstanceUpdate(
            name="Acme Renamed Corp",
            username="new_sc_user",
            password="new_secret_pwd",
        ),
    )
    assert up_rec is not None
    assert up_rec.name == "Acme Renamed Corp"
    assert up_rec.username == "new_sc_user"
    assert up_rec.password == "new_secret_pwd"

    # Update non-existent returns None
    assert repo.update_instance("ghost", InstanceUpdate(name="G")) is None

    # Delete instance
    assert repo.delete_instance("acme-sandbox") is True
    assert repo.get_instance("acme-sandbox") is None
    assert repo.delete_instance("ghost") is False
    conn.close()


def test_template_registry_lifecycle() -> None:
    """Test saving and retrieving reusable customization templates."""
    conn = init_db(":memory:")
    repo = DatabaseRepository(conn)

    assert repo.list_templates() == []

    repo.save_template(
        TemplateRecord(
            id="incident-router-template",
            name="GenAI Incident Router Template",
            description="Autonomous AI incident triage with customer branding",
            version="1.0.0",
            base_bundle_id="sample-ai-assistant",
            parameters_schema={
                "customer_name": {"type": "string", "default": "Acme Corp"},
                "primary_color": {"type": "string", "default": "#23a17e"},
            },
        )
    )

    templates = repo.list_templates()
    assert len(templates) == 1
    assert templates[0].id == "incident-router-template"
    assert templates[0].parameters_schema["customer_name"]["default"] == "Acme Corp"
    conn.close()


def test_seed_default_instance_if_empty() -> None:
    """Verify seeding default instance into empty connection when settings configured."""
    from now_workbench.config.settings import settings
    from now_workbench.db.session import seed_default_instance_if_empty

    # Test when settings has no instance url
    old_url = settings.sn_instance_url
    old_user = settings.sn_username
    old_pw = settings.sn_password
    try:
        settings.sn_instance_url = ""
        conn_empty = init_db(":memory:")
        seed_default_instance_if_empty(conn_empty)
        assert DatabaseRepository(conn_empty).list_instances() == []
        conn_empty.close()

        # Test when settings has an instance url
        settings.sn_instance_url = "https://default-test.service-now.com"
        settings.sn_username = "admin"
        settings.sn_password = "password123"

        conn = init_db(":memory:")
        seed_default_instance_if_empty(conn)
        repo = DatabaseRepository(conn)
        # No administrator yet: the instance waits, orphaned, for the first one (ADR-018).
        with owner_scope(""):
            instances = repo.list_instances()
            assert len(instances) == 1
            assert instances[0].id == "primary-instance"
            assert instances[0].url == "https://default-test.service-now.com"

            # Calling again when non-empty does not re-add
            seed_default_instance_if_empty(conn)
            assert len(repo.list_instances()) == 1
        conn.close()
    finally:
        settings.sn_instance_url = old_url
        settings.sn_username = old_user
        settings.sn_password = old_pw


def test_init_db_file_and_get_db_path(tmp_path: Path) -> None:
    """Verify file-based SQLite database initialization with WAL mode."""
    from now_workbench.db.session import get_db_path

    db_file = tmp_path / "custom.db"
    conn = init_db(db_file)
    try:
        assert db_file.exists()
        row = conn.execute("PRAGMA foreign_keys;").fetchone()
        assert row[0] == 1
    finally:
        conn.close()

    default_path = get_db_path()
    assert default_path.name == "workbench.db"


def test_db_session_and_chat_threads_lifecycle() -> None:
    """Verify db_session context manager and conversational thread/message CRUD."""
    with db_session(":memory:") as repo:
        assert repo.list_threads() == []
        assert repo.get_thread("missing-thread") is None

        thread = repo.create_thread(ChatThreadCreate(id="t-100", title="Initial Thread"))
        assert thread.id == "t-100"
        assert thread.title == "Initial Thread"

        fetched = repo.get_thread("t-100")
        assert fetched is not None
        assert fetched.title == "Initial Thread"
        assert len(repo.list_threads()) == 1

        # Add user and assistant messages
        msg1 = repo.add_message(
            ChatMessageRecord(
                id="m-1",
                thread_id="t-100",
                role="user",
                content="Show me instance options",
            )
        )
        assert msg1.id == "m-1"

        msg2 = repo.add_message(
            ChatMessageRecord(
                id="m-2",
                thread_id="t-100",
                role="assistant",
                content="Here are your instances",
                widget_type="instance_selector",
                widget_data={"count": 2},
            )
        )
        assert msg2.widget_type == "instance_selector"

        messages = repo.list_messages("t-100")
        assert len(messages) == 2
        assert messages[0].content == "Show me instance options"
        assert messages[1].widget_data == {"count": 2}

        # Update (archive & rename) and delete thread
        from now_workbench.db.models import ChatThreadUpdate

        updated = repo.update_thread(
            "t-100", ChatThreadUpdate(title="Archived Thread", archived=True)
        )
        assert updated is not None
        assert updated.title == "Archived Thread"
        assert updated.archived is True
        assert updated.tokens_used == 0
        assert repo.list_threads(include_archived=False) == []
        assert len(repo.list_threads(include_archived=True)) == 1
        assert repo.update_thread("missing", ChatThreadUpdate(archived=False)) is None

        assert repo.delete_thread("t-100") is True
        assert repo.get_thread("t-100") is None
        assert repo.list_messages("t-100") == []
        assert repo.delete_thread("t-100") is False


def test_get_default_instance_fallback_when_none_marked() -> None:
    """Verify get_default_instance promotes first instance when none is marked default."""
    conn = init_db(":memory:")
    repo = DatabaseRepository(conn)
    inst = repo.add_instance(
        InstanceCreate(
            name="Fallback Inst",
            url="https://fallback.service-now.com",
            username="admin",
            password="pwd",
            is_default=False,
        )
    )
    conn.execute("UPDATE instances SET is_default = 0;")
    fetched = repo.get_default_instance()
    assert fetched is not None
    assert fetched.id == inst.id
    assert fetched.is_default is True
    conn.close()


def test_update_instance_without_password_keeps_password_encrypted() -> None:
    """Verify a non-credential update never rewrites the stored password as plaintext."""
    conn = init_db(":memory:")
    repo = DatabaseRepository(conn)
    inst = repo.add_instance(
        InstanceCreate(
            name="Enc Inst",
            url="https://enc.service-now.com",
            username="admin",
            password="S3cret!",
        )
    )
    repo.update_instance(inst.id, InstanceUpdate(name="Enc Inst Renamed"))
    sealed = conn.execute(
        "SELECT credentials_sealed FROM instances WHERE id = ?;", (inst.id,)
    ).fetchone()["credentials_sealed"]
    assert b"S3cret!" not in sealed
    fetched = repo.get_instance(inst.id)
    assert fetched is not None
    assert fetched.password == "S3cret!"
    conn.close()
