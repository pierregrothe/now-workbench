"""Dynamic Date Wizard engine for resolving relative timestamps in demo datasets."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

# Matches {{TODAY}}, {{NOW}}, {{TODAY - 2h}}, {{TODAY + 3d}}, etc.
_DATE_EXPR_PATTERN = re.compile(
    r"\{\{\s*(TODAY|NOW)\s*(?:([+-])\s*(\d+)\s*([smhdw]))?\s*\}\}",
    re.IGNORECASE,
)


def resolve_date_expression(expr: str, anchor: datetime | None = None) -> str:
    """Resolve a single relative date expression to an ISO/ServiceNow UTC timestamp string."""
    now = anchor or datetime.now(UTC)

    def _replace_match(match: re.Match[str]) -> str:
        sign = match.group(2)
        amount_str = match.group(3)
        unit = (match.group(4) or "").lower()

        if not sign or not amount_str:
            return now.strftime("%Y-%m-%d %H:%M:%S")

        amount = int(amount_str)
        delta = timedelta()
        if unit == "s":
            delta = timedelta(seconds=amount)
        elif unit == "m":
            delta = timedelta(minutes=amount)
        elif unit == "h":
            delta = timedelta(hours=amount)
        elif unit == "d":
            delta = timedelta(days=amount)
        elif unit == "w":
            delta = timedelta(weeks=amount)

        target_time = (now + delta) if sign == "+" else (now - delta)
        return target_time.strftime("%Y-%m-%d %H:%M:%S")

    return _DATE_EXPR_PATTERN.sub(_replace_match, expr)


def transform_dataset_dates(obj: Any, anchor: datetime | None = None) -> Any:
    """Recursively transform all date expressions across strings, lists, and dicts."""
    if isinstance(obj, str):
        if "{{" in obj and "}}" in obj:
            return resolve_date_expression(obj, anchor=anchor)
        return obj
    if isinstance(obj, list):
        return [transform_dataset_dates(item, anchor=anchor) for item in obj]
    if isinstance(obj, dict):
        return {k: transform_dataset_dates(v, anchor=anchor) for k, v in obj.items()}
    return obj
