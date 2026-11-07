# src/now_workbench/domains/properties/__init__.py
# Public root of the properties domain: other packages import only what is listed here.
# Author: Pierre Grothe
# Date: 2026-11-07
"""System property management and transactional restoration for demo bundles."""

from now_workbench.domains.properties.engine import PropertyEngine
from now_workbench.domains.properties.models import (
    PropertyApplyResult,
    PropertyRecord,
    PropertySnapshot,
)

__all__ = [
    "PropertyApplyResult",
    "PropertyEngine",
    "PropertyRecord",
    "PropertySnapshot",
]
