# tests/test_policy_guards.py
# Mechanical checks for the otto-copilot, demo-bundles and sqlite-persistence policies (STORY-060).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Policy guards; each test names the registry policy it enforces (policies/registry.yaml)."""

import ast
import json
import sqlite3
from pathlib import Path

import pytest

from now_workbench.domains.bundles.models import DemoManifest
from now_workbench.platform.db.session import init_db

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "now_workbench"


def _modules() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def _calls(path: Path, method: str) -> list[int]:
    return [
        node.lineno
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == method
    ]


# --------------------------------------------------------------------------- otto-copilot


def test_otto_copilot_policy_claude_sdk_only_in_the_ai_interface() -> None:
    """Policy otto-copilot (ADR-002, ADR-011): Claude is reached only through interfaces/ai."""
    users = {str(p.relative_to(SRC)) for p in _modules() if "anthropic" in _imports(p)}
    assert users == {"interfaces/ai/agent.py", "interfaces/ai/client.py"}


# --------------------------------------------------------------------------- sqlite-persistence


def _is_persistence(path: Path) -> bool:
    rel = path.relative_to(SRC)
    return rel.parts[:2] == ("platform", "db") or "repository" in path.stem


def test_sqlite_persistence_policy_sql_only_in_repositories() -> None:
    """Policy sqlite-persistence (ADR-006): SQL runs only in repositories and platform/db."""
    outside = [
        f"{p.relative_to(SRC)}:{line}"
        for p in _modules()
        if not _is_persistence(p)
        for method in ("execute", "executescript", "executemany")
        for line in _calls(p, method)
    ]
    assert outside == []


def test_sqlite_persistence_policy_file_databases_use_wal(tmp_path: Path) -> None:
    """Policy sqlite-persistence (ADR-006): a file database runs in WAL mode."""
    conn = init_db(tmp_path / "wal.db")
    try:
        assert conn.execute("PRAGMA journal_mode;").fetchone()[0] == "wal"
    finally:
        conn.close()
    raw = sqlite3.connect(tmp_path / "wal.db")
    assert raw.execute("PRAGMA journal_mode;").fetchone()[0] == "wal"  # persists in the file
    raw.close()


# --------------------------------------------------------------------------- demo-bundles


@pytest.mark.parametrize(
    "manifest", sorted((ROOT / "bundles").glob("*/manifest.json")), ids=lambda p: p.parent.name
)
def test_demo_bundles_policy_every_shipped_manifest_validates(manifest: Path) -> None:
    """Policy demo-bundles (ADR-003): every shipped bundle declares a valid manifest."""
    parsed = DemoManifest.model_validate(json.loads(manifest.read_text()))
    assert parsed.id == manifest.parent.name


def test_demo_bundles_policy_ships_bundles() -> None:
    """The bundle check above must have something to check."""
    assert len(list((ROOT / "bundles").glob("*/manifest.json"))) >= 3


# --------------------------------------------------------------------------- the guards bite


def test_policy_guards_detect_a_violation(tmp_path: Path) -> None:
    """Each check finds a planted violation, so a pass means the rule holds."""
    bad = tmp_path / "service.py"
    bad.write_text(
        "import anthropic\n"
        "from anthropic import Anthropic\n"
        "def f(conn):\n"
        "    conn.execute('DELETE FROM users')\n"
        "    conn.executescript('VACUUM')\n"
    )
    assert "anthropic" in _imports(bad)
    assert _calls(bad, "execute") == [4]
    assert _calls(bad, "executescript") == [5]
    with pytest.raises(ValueError):
        DemoManifest.model_validate({"id": "x", "unknown_field": True})
