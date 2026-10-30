# ADR-006: Local SQLite WAL Persistence and Scoped Repository Pattern

**Status:** accepted
**Date:** 2026-10-29

## Context

`now-workbench` manages stateful local resources across both the Typer CLI and the FastAPI
server: registered ServiceNow instances (`instances`), reusable customer customization
templates (`templates`), conversational workspace threads and messages (`chat_threads`,
`chat_messages`), and transactional seed rollback audit logs (`seed_operations`).

Early iterations opened ad-hoc `sqlite3.Connection` objects without deterministic closure,
causing `ResourceWarning`s under test and risking lock contention when concurrent FastAPI
requests and CLI commands accessed the database.

## Decision

1. **Embedded SQLite with WAL Mode**:
   - Store local state in `<data_dir>/workbench.db` (overridable via `WORKBENCH_DB_PATH`).
   - Enable Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) and foreign key enforcement
     (`PRAGMA foreign_keys=ON;`) on connection initialization in `init_db()`.
2. **Scoped Context Manager (`db_session`)**:
   - All database interactions in API routes and CLI commands must use the `with db_session() as repo:`
     context manager, which wraps `DatabaseRepository(conn)` and guarantees `conn.close()` on exit.
3. **Immutable Pydantic Boundary (`DatabaseRepository`)**:
   - `DatabaseRepository` encapsulates all SQL queries and returns frozen Pydantic v2 models
     (`InstanceRecord`, `TemplateRecord`, `ChatThreadRecord`, `ChatMessageRecord`,
     `SeedOperationRecord`), preventing raw `sqlite3.Row` leakage into application logic.

## Consequences

- Zero unclosed database connection warnings across the entire test suite and runtime.
- Safe concurrent reads and serialized writes between the FastAPI server and CLI commands.
- Deterministic in-memory testing via `db_session(":memory:")` or `WORKBENCH_DB_PATH`.
