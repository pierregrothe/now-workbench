"""Repository layer providing typed SQLite data access for now-workbench (ADR-011)."""

import sqlite3
from typing import Any, Self

from now_workbench.db.repos import (
    InstanceRepositoryMixin,
    PreferencesRepositoryMixin,
    SeedRepositoryMixin,
    TemplateRepositoryMixin,
    ThreadRepositoryMixin,
    row_to_instance,
)

_row_to_instance = row_to_instance


class DatabaseRepository(
    InstanceRepositoryMixin,
    TemplateRepositoryMixin,
    ThreadRepositoryMixin,
    SeedRepositoryMixin,
    PreferencesRepositoryMixin,
):
    """Encapsulates SQLite queries for instances, templates, threads, seeds, and preferences."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self.conn.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
