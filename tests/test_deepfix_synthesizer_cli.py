# tests/test_deepfix_synthesizer_cli.py
# Regression tests for capture_demo_cmd instance resolution (no hardcoded fallback)
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests that capture_demo_cmd fails clearly when no instance is registered."""

import typer
from typer.testing import CliRunner

from now_workbench.db.session import db_session
from now_workbench.synthesizer.cli import capture_demo_cmd

_app = typer.Typer()
_app.command()(capture_demo_cmd)


def _clear_instances() -> None:
    """Remove the fixture-seeded instance from the isolated per-test database."""
    with db_session() as repo:
        for inst in repo.list_instances():
            repo.delete_instance(inst.id)


def test_capture_demo_cmd_no_default_instance_exits_1() -> None:
    _clear_instances()
    result = CliRunner().invoke(_app, ["--fake"])
    assert result.exit_code == 1
    assert "No default instance registered" in result.output


def test_capture_demo_cmd_unknown_instance_exits_1() -> None:
    result = CliRunner().invoke(_app, ["--fake", "--instance", "does-not-exist"])
    assert result.exit_code == 1
    assert "does-not-exist" in result.output
