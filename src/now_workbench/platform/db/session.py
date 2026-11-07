# src/now_workbench/platform/db/session.py
# SQLite connections, pragmas and the one-time schema migration of each database file.
# Author: Pierre Grothe
# Date: 2026-11-07
"""SQLite connection management and one-time schema migration (ADR-006, ADR-012).

The platform knows no domain. Work that must follow a migration (seeding the configured
instance) is registered by the composition root with :func:`on_migrated` (ADR-015).
"""

import logging
import os
import sqlite3
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from now_workbench.platform.db.schema import SCHEMA_VERSION, apply_migrations

__all__ = ["db_session", "get_db_path", "init_db", "on_migrated"]

logger = logging.getLogger(__name__)

_MEMORY = ":memory:"
_BUSY_TIMEOUT_MS = 5000
_migration_lock = threading.Lock()
_after_migration: list[Callable[[sqlite3.Connection], None]] = []


def on_migrated(hook: Callable[[sqlite3.Connection], None]) -> None:
    """Run ``hook`` on a database file right after it is created or migrated.

    Args:
        hook: Receives the migrated connection; registering the same hook twice is a no-op.
    """
    if hook not in _after_migration:
        _after_migration.append(hook)


def get_db_path() -> Path:
    """Return the resolved path to the local SQLite database file."""
    from now_workbench.platform.config.settings import settings

    env_db = os.environ.get("WORKBENCH_DB_PATH")
    if env_db:
        db_path = Path(env_db).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return db_path

    data_dir = settings.get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "workbench.db"


def _connect(target: str) -> sqlite3.Connection:
    """Open a connection with the per-connection pragmas every session needs."""
    conn = sqlite3.connect(target, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS};")
    if target != _MEMORY:
        # WAL persists in the file; NORMAL sync is durable-on-checkpoint and safe under WAL.
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def _is_unversioned_prototype(conn: sqlite3.Connection) -> bool:
    """Detect a pre-ADR-012 prototype database (tables present, user_version 0)."""
    version = _schema_version(conn)
    has_tables = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' LIMIT 1;"
    ).fetchone()
    return version == 0 and has_tables is not None


def _retire_prototype(target: Path) -> Path:
    """Move a prototype database (and WAL sidecars) aside so a clean v1 schema starts."""
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup = target.with_name(f"{target.name}.prototype-{stamp}.bak")
    target.rename(backup)
    for suffix in ("-wal", "-shm"):
        sidecar = target.with_name(target.name + suffix)
        if sidecar.exists():
            sidecar.rename(backup.with_name(backup.name + suffix))
    logger.warning("Prototype database moved to %s; started a fresh schema.", backup)
    return backup


def _schema_version(conn: sqlite3.Connection) -> int:
    """Return the schema version recorded in the database header."""
    return int(conn.execute("PRAGMA user_version;").fetchone()[0])


def _prepare_file_db(target: str) -> None:
    """Retire a prototype file, migrate, and run the post-migration hooks (serialized)."""
    with _migration_lock:
        conn = _connect(target)
        try:
            if _schema_version(conn) == SCHEMA_VERSION:
                return
            if _is_unversioned_prototype(conn):
                conn.close()
                _retire_prototype(Path(target))
                conn = _connect(target)
            apply_migrations(conn)
            for hook in _after_migration:
                hook(conn)
        finally:
            conn.close()


def init_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Return a ready connection; the schema is migrated on first use of each path.

    Args:
        db_path: File path or ``":memory:"``; defaults to ``get_db_path()``.

    Returns:
        An open connection with foreign keys, busy timeout, and WAL configured.
    """
    target = str(db_path) if db_path is not None else str(get_db_path())
    if target == _MEMORY:
        conn = _connect(target)
        apply_migrations(conn)
        return conn
    conn = _connect(target)
    if _schema_version(conn) == SCHEMA_VERSION:
        return conn
    conn.close()
    _prepare_file_db(target)
    return _connect(target)


@contextmanager
def db_session(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    """Yield a migrated connection and guarantee it is closed.

    Domains wrap it in their own repositories (``ThreadRepository(conn)``); one connection
    is the unit of work shared by every repository opened on it (ADR-015).
    """
    conn = init_db(db_path=db_path)
    try:
        yield conn
    finally:
        conn.close()
