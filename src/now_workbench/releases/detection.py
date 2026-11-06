# src/now_workbench/releases/detection.py
# Parse the ServiceNow release family from an instance's build identifier.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Release family detection from the ``glide.war`` system property.

Every instance exposes its build as ``glide.war``, e.g.
``glide-australia-02-11-2026__patch7w42-10-08-2026_10-13-2026_1248.zip``.
The token after ``glide-`` is the release family in compact lowercase form
(``australia``, ``washingtondc``, ``sandiego``).
"""

import re

from now_workbench.releases.compatibility import normalize_release

__all__ = ["BUILD_PROPERTY", "parse_release_family"]

BUILD_PROPERTY = "glide.war"

_WAR_PATTERN = re.compile(r"^glide-([a-z]+)-\d{2}-\d{2}-\d{4}")


def parse_release_family(build: str) -> str | None:
    """Return the release family named by a ``glide.war`` value.

    Args:
        build: Raw ``glide.war`` property value.

    Returns:
        The family display name (e.g. ``"Australia"``, ``"Washington DC"``), or
        ``None`` when the value does not look like a ServiceNow build identifier.
    """
    match = _WAR_PATTERN.match(build.strip().lower())
    return normalize_release(match.group(1)) if match else None
