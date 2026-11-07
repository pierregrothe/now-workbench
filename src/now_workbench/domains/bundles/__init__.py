# src/now_workbench/domains/bundles/__init__.py
# Public root of the bundles domain: other packages import only what is listed here.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Bundles package."""

from now_workbench.domains.bundles.manager import BundleManager
from now_workbench.domains.bundles.models import DemoBundleInfo, DemoManifest, DemoPersona

__all__ = [
    "BundleManager",
    "DemoBundleInfo",
    "DemoManifest",
    "DemoPersona",
]
