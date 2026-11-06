# src/now_workbench/db/schema.py
# Versioned SQLite schema migrations tracked by PRAGMA user_version (ADR-012).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Versioned SQLite schema for now-workbench (ADR-012).

``MIGRATIONS[n]`` upgrades a database from ``user_version == n`` to ``n + 1``.
Migrations are append-only: never edit a shipped entry, add a new one.
All timestamps are UTC ISO-8601 TEXT with a ``Z`` suffix (``_NOW``).
"""

import sqlite3

__all__ = ["MIGRATIONS", "SCHEMA_VERSION", "apply_migrations"]

_NOW = "(strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"

_V1 = f"""
CREATE TABLE instances (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL COLLATE NOCASE UNIQUE,
    url                 TEXT NOT NULL,
    auth_type           TEXT NOT NULL DEFAULT 'basic'
                        CHECK (auth_type IN ('basic', 'oauth', 'token')),
    credentials_sealed  BLOB NOT NULL,
    release             TEXT NOT NULL DEFAULT 'Zurich',
    is_default          INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
    status              TEXT NOT NULL DEFAULT 'unknown',
    last_checked        TEXT,
    created_at          TEXT NOT NULL DEFAULT {_NOW},
    updated_at          TEXT NOT NULL DEFAULT {_NOW}
) STRICT;

-- At most one default instance, enforced by the engine instead of app code.
CREATE UNIQUE INDEX ux_instances_single_default ON instances (is_default) WHERE is_default = 1;

CREATE TABLE instance_plugins (
    instance_id   TEXT NOT NULL REFERENCES instances (id) ON DELETE CASCADE,
    plugin_id     TEXT NOT NULL,
    plugin_name   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'active',
    installed_at  TEXT NOT NULL DEFAULT {_NOW},
    PRIMARY KEY (instance_id, plugin_id)
) STRICT, WITHOUT ROWID;

CREATE TABLE templates (
    id                 TEXT PRIMARY KEY,
    name               TEXT NOT NULL,
    description        TEXT NOT NULL,
    version            TEXT NOT NULL DEFAULT '1.0.0',
    base_bundle_id     TEXT NOT NULL,
    parameters_schema  TEXT NOT NULL DEFAULT '{{}}' CHECK (json_valid(parameters_schema))
) STRICT;

CREATE TABLE chat_threads (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    archived    INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1)),
    target_tab  TEXT NOT NULL DEFAULT 'home',
    created_at  TEXT NOT NULL DEFAULT {_NOW},
    updated_at  TEXT NOT NULL DEFAULT {_NOW}
) STRICT;

CREATE INDEX ix_chat_threads_updated ON chat_threads (archived, updated_at DESC);

CREATE TABLE chat_messages (
    id           TEXT PRIMARY KEY,
    thread_id    TEXT NOT NULL REFERENCES chat_threads (id) ON DELETE CASCADE,
    role         TEXT NOT NULL,
    content      TEXT NOT NULL,
    widget_type  TEXT,
    widget_data  TEXT CHECK (widget_data IS NULL OR json_valid(widget_data)),
    created_at   TEXT NOT NULL DEFAULT {_NOW}
) STRICT;

CREATE INDEX ix_chat_messages_thread ON chat_messages (thread_id, created_at);

-- Audit log: deliberately NO foreign key to instances, so history survives
-- an instance being removed from the registry.
CREATE TABLE seed_operations (
    id               TEXT PRIMARY KEY,
    bundle_id        TEXT NOT NULL,
    instance_id      TEXT NOT NULL,
    status           TEXT NOT NULL,
    created_records  TEXT NOT NULL CHECK (json_valid(created_records)),
    created_at       TEXT NOT NULL DEFAULT {_NOW}
) STRICT;

CREATE INDEX ix_seed_operations_created ON seed_operations (created_at DESC);

-- Singleton row of non-secret preferences, validated by Pydantic on read.
CREATE TABLE workbench_preferences (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    payload     TEXT NOT NULL CHECK (json_valid(payload)),
    updated_at  TEXT NOT NULL DEFAULT {_NOW}
) STRICT;

-- Named application secrets (e.g. the Claude API key), sealed with AES-256-GCM.
CREATE TABLE secrets (
    name        TEXT PRIMARY KEY,
    sealed      BLOB NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT {_NOW}
) STRICT, WITHOUT ROWID;
"""

# v2 (ADR-014): the release is detected from the instance, never user-entered. The
# platform profile (build, environment, datacenter, nodes, CPU, memory) is captured
# on every successful connection test.
_V2 = f"""
ALTER TABLE instances DROP COLUMN release;

CREATE TABLE instance_profiles (
    instance_id     TEXT PRIMARY KEY REFERENCES instances (id) ON DELETE CASCADE,
    release         TEXT,
    build_tag       TEXT,
    build_date      TEXT,
    platform_name   TEXT,
    environment     TEXT,
    is_production   INTEGER CHECK (is_production IS NULL OR is_production IN (0, 1)),
    datacenter      TEXT,
    db_product      TEXT,
    db_version      TEXT,
    java_version    TEXT,
    os              TEXT,
    captured_at     TEXT NOT NULL DEFAULT {_NOW}
) STRICT;

CREATE TABLE instance_nodes (
    instance_id      TEXT NOT NULL REFERENCES instances (id) ON DELETE CASCADE,
    node_id          TEXT NOT NULL,
    hostname         TEXT NOT NULL,
    datacenter       TEXT,
    status           TEXT NOT NULL,
    cpu_count        INTEGER,
    memory_max_mb    REAL,
    memory_in_use_mb REAL,
    memory_pressure  TEXT,
    started_at       TEXT,
    PRIMARY KEY (instance_id, node_id)
) STRICT, WITHOUT ROWID;
"""

# v3 (ADR-014 amendment): separate what ServiceNow *reports* from what the owner
# *intends*. instance_type / production_property are platform-reported provisioning
# facts (a standalone demo instance reports "prod"); purpose is user-declared.
_V3 = """
ALTER TABLE instances ADD COLUMN purpose TEXT NOT NULL DEFAULT 'demo'
    CHECK (purpose IN ('demo', 'development', 'test', 'production'));

ALTER TABLE instance_profiles RENAME COLUMN environment TO instance_type;
ALTER TABLE instance_profiles RENAME COLUMN is_production TO production_property;
ALTER TABLE instance_profiles ADD COLUMN installation_name TEXT;
"""

# v4: the default release preference is gone; a bundle's release is detected from the
# target instance (ADR-014). Strip the key so stored preferences still validate.
_V4 = """
UPDATE workbench_preferences SET payload = json_remove(payload, '$.default_sn_release');
"""

# v5: one profile per signed-in user, keyed by the email Cloudflare Access verified (ADR-016).
_V5 = f"""
CREATE TABLE profile (
    email              TEXT PRIMARY KEY,
    display_name       TEXT NOT NULL DEFAULT '',
    avatar_kind        TEXT NOT NULL DEFAULT 'none'
                       CHECK (avatar_kind IN ('none', 'preset', 'upload')),
    avatar_preset      TEXT,
    avatar_updated_at  TEXT,
    updated_at         TEXT NOT NULL DEFAULT {_NOW}
) STRICT, WITHOUT ROWID;
"""

# v6: people allowed in and their roles (ADR-017). Cloudflare Access proves the email; this
# table says what that email may do. The first admin is created by the first-run setup code.
_V6 = f"""
CREATE TABLE users (
    email          TEXT PRIMARY KEY,
    is_admin       INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1)),
    is_consultant  INTEGER NOT NULL DEFAULT 0 CHECK (is_consultant IN (0, 1)),
    added_by       TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL DEFAULT {_NOW},
    updated_at     TEXT NOT NULL DEFAULT {_NOW},
    CHECK (is_admin = 1 OR is_consultant = 1)
) STRICT, WITHOUT ROWID;
"""

MIGRATIONS: tuple[str, ...] = (_V1, _V2, _V3, _V4, _V5, _V6)
SCHEMA_VERSION = len(MIGRATIONS)


def apply_migrations(conn: sqlite3.Connection) -> int:
    """Upgrade the database to ``SCHEMA_VERSION``, one transaction per step.

    Args:
        conn: Open connection (autocommit or default isolation).

    Returns:
        The schema version after migrating.

    Raises:
        RuntimeError: The database was written by a newer schema version.
    """
    current = int(conn.execute("PRAGMA user_version;").fetchone()[0])
    if current > SCHEMA_VERSION:
        msg = f"Database schema v{current} is newer than this build (v{SCHEMA_VERSION})."
        raise RuntimeError(msg)
    for version in range(current, SCHEMA_VERSION):
        script = f"{MIGRATIONS[version]}\nPRAGMA user_version = {version + 1};"
        try:
            conn.executescript(f"BEGIN IMMEDIATE;\n{script}\nCOMMIT;")
        except sqlite3.Error:
            if conn.in_transaction:
                conn.execute("ROLLBACK;")
            raise
    return SCHEMA_VERSION
