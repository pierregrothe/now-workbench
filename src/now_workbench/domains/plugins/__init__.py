# src/now_workbench/domains/plugins/__init__.py
# Public root of the plugins domain: other packages import only what is listed here.
# Author: Pierre Grothe
# Date: 2026-11-07
"""ServiceNow instance plugins and module management."""

from now_workbench.domains.plugins.manager import PluginManager
from now_workbench.domains.plugins.models import PluginEvaluationResult, PluginRecord

__all__ = [
    "PluginEvaluationResult",
    "PluginManager",
    "PluginRecord",
]
