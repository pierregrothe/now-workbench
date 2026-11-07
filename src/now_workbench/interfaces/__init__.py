# src/now_workbench/interfaces/__init__.py
# Delivery layer (API, CLI, Otto) and the composition root that wires domains to the platform.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Interfaces layer (ADR-015).

Importing any interface (``interfaces.api``, ``interfaces.cli``, ``interfaces.ai``) runs this
module first, so the platform hooks below are in place before the first database is opened.
"""

from now_workbench.domains.instances import seed_default_instance_if_empty
from now_workbench.platform.db.session import on_migrated

__all__: list[str] = []

on_migrated(seed_default_instance_if_empty)
