# src/now_workbench/interfaces/api/retention.py
# Purges telemetry past its retention window, at startup and every day after (ADR-029).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Telemetry retention while the server runs."""

import asyncio
import logging
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from now_workbench.domains.telemetry import purge_expired
from now_workbench.platform.clock import utc_now
from now_workbench.platform.config.settings import settings
from now_workbench.platform.db.session import db_session

__all__ = ["purge_telemetry", "telemetry_retention"]

_log = logging.getLogger(__name__)
_DAY_SECONDS = 86_400.0


def purge_telemetry() -> int:
    """Delete the telemetry older than `settings.telemetry_retention_days`.

    Returns:
        The number of events deleted (0 when the purge failed; the failure is logged).
    """
    try:
        with db_session() as conn:
            gone = purge_expired(conn, settings.telemetry_retention_days, utc_now())
    except sqlite3.Error:
        _log.exception("Telemetry purge failed; events are kept until the next run.")
        return 0
    if gone:
        _log.info(
            "Telemetry purge: %d events older than %d days deleted.",
            gone,
            settings.telemetry_retention_days,
        )
    return gone


async def _every(interval: float) -> None:
    while True:
        await asyncio.sleep(interval)
        await asyncio.to_thread(purge_telemetry)


@asynccontextmanager
async def telemetry_retention(interval: float = _DAY_SECONDS) -> AsyncIterator[None]:
    """Purge now and then every `interval` seconds until the context exits.

    Args:
        interval: Seconds between purges (a day; shorter in tests).
    """
    purge_telemetry()
    task = asyncio.create_task(_every(interval))
    try:
        yield
    finally:
        task.cancel()
