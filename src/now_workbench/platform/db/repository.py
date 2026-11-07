# src/now_workbench/platform/db/repository.py
# Shared base for the per-domain repositories over one SQLite connection.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Repository base (ADR-015).

Each domain owns a repository class; every repository opened on the same connection shares
its transaction, so a caller combines several of them in one unit of work.
"""

import sqlite3

__all__ = ["Repository"]


class Repository:
    """Base class holding the connection a domain repository works on.

    Args:
        conn: An open connection from ``db_session()`` or ``init_db()``.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
