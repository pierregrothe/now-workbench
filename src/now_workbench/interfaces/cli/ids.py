# src/now_workbench/interfaces/cli/ids.py
# One check for every CLI argument that names a bundle, template or capture file.
# Author: Pierre Grothe
# Date: 2026-11-07
"""CLI identifier check.

The API answers 400 to an identifier that could escape its folder (`safe_child`); the CLI
applies the same rule before a command runs, so `workbench demo inspect ../../etc` exits
with a usage error and touches no file.
"""

import typer

from now_workbench.platform.config.paths import UnsafePathError, check_name

__all__ = ["safe_id"]


def safe_id(value: str | None) -> str | None:
    """Typer callback: pass a safe identifier through, refuse anything else (exit code 2).

    Args:
        value: The argument as typed (None when an optional argument is omitted).

    Returns:
        The identifier unchanged.

    Raises:
        typer.BadParameter: The identifier could leave its folder.
    """
    if value is None:
        return None
    try:
        return check_name(value)
    except UnsafePathError as exc:
        raise typer.BadParameter(str(exc)) from exc
