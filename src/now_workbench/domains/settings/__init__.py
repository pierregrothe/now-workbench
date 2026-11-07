# src/now_workbench/domains/settings/__init__.py
# Public root of the settings domain: other packages import only what is listed here.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Settings domain (ADR-015)."""

from now_workbench.domains.settings.models import WorkbenchPreferences, WorkbenchPreferencesUpdate
from now_workbench.domains.settings.repository import PreferencesRepository

__all__ = [
    "PreferencesRepository",
    "WorkbenchPreferences",
    "WorkbenchPreferencesUpdate",
]
