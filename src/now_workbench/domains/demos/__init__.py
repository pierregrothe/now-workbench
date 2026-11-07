# src/now_workbench/domains/demos/__init__.py
# Public root of the demos domain: other packages import only what is listed here.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Demos domain (ADR-015)."""

from now_workbench.domains.demos.pipeline import (
    DemoEvaluationResult,
    DemoPipelineEngine,
    DemoPipelineSummary,
)

__all__ = [
    "DemoEvaluationResult",
    "DemoPipelineEngine",
    "DemoPipelineSummary",
]
