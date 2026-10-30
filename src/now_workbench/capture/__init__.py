"""Playwright screenshot and video capture engine for ServiceNow instances."""

from now_workbench.capture.engine import PlaywrightCaptureEngine
from now_workbench.capture.models import CaptureArtifact, CaptureRequest

__all__ = [
    "CaptureArtifact",
    "CaptureRequest",
    "PlaywrightCaptureEngine",
]
