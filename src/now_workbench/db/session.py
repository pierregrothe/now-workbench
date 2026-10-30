"""SQLite database connection and schema initialization for now-workbench."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from now_workbench.db.repository import DatabaseRepository


def get_db_path() -> Path:
    """Return the resolved path to the local SQLite database file."""
    from now_workbench.config.settings import settings

    env_db = os.environ.get("WORKBENCH_DB_PATH")
    if env_db:
        db_path = Path(env_db).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path

    env_data = os.environ.get("WORKBENCH_DATA_DIR")
    data_dir = Path(env_data).resolve() if env_data else settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "workbench.db"


@contextmanager
def db_session(db_path: str | Path | None = None) -> Iterator[DatabaseRepository]:
    """Context manager yielding a DatabaseRepository and ensuring connection closure."""
    with DatabaseRepository(init_db(db_path=db_path)) as repo:
        yield repo


def init_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Initialize database schema, apply migrations, and enable WAL mode."""
    target = str(db_path) if db_path is not None else str(get_db_path())
    conn = sqlite3.connect(target, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    if target != ":memory:":
        conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")

    # Schema Migrations
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS instances (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                username TEXT NOT NULL DEFAULT 'admin',
                password TEXT NOT NULL DEFAULT '',
                auth_type TEXT NOT NULL DEFAULT 'basic',
                release TEXT NOT NULL DEFAULT 'Zurich',
                is_default INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'unknown',
                last_checked TEXT
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                version TEXT NOT NULL DEFAULT '1.0.0',
                base_bundle_id TEXT NOT NULL,
                parameters_schema TEXT NOT NULL DEFAULT '{}'
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_threads (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0,
                target_tab TEXT NOT NULL DEFAULT 'home',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        existing_cols = {
            row["name"] for row in conn.execute("PRAGMA table_info(chat_threads);").fetchall()
        }
        if "archived" not in existing_cols:
            conn.execute("ALTER TABLE chat_threads ADD COLUMN archived INTEGER NOT NULL DEFAULT 0;")
        if "target_tab" not in existing_cols:
            conn.execute(
                "ALTER TABLE chat_threads ADD COLUMN target_tab TEXT NOT NULL DEFAULT 'home';"
            )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                widget_type TEXT,
                widget_data TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seed_operations (
                id TEXT PRIMARY KEY,
                bundle_id TEXT NOT NULL,
                instance_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_records TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workbench_preferences (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS instance_plugins (
                instance_id TEXT NOT NULL,
                plugin_id TEXT NOT NULL,
                plugin_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                installed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (instance_id, plugin_id),
                FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE
            );
            """
        )

    if target != ":memory:":
        seed_default_instance_if_empty(conn)

    return conn


def seed_default_instance_if_empty(conn: sqlite3.Connection) -> None:
    """Seed initial instance from settings if registry is currently empty."""
    from now_workbench.config.settings import settings
    from now_workbench.db.models import InstanceCreate
    from now_workbench.db.repository import DatabaseRepository

    if not settings.sn_instance_url:
        return
    repo = DatabaseRepository(conn)
    if not repo.list_instances():
        repo.add_instance(
            InstanceCreate(
                id="primary-instance",
                name="Primary Instance",
                url=settings.sn_instance_url,
                username=settings.sn_username or "admin",
                password=settings.sn_password,
                auth_type="basic",
                release="Zurich",
                is_default=True,
            )
        )
