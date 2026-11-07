# tests/test_paths_and_origins.py
# Tests for path containment, origin matching, and the loopback settings defaults.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for now_workbench.config.paths, .origins and the security defaults in settings."""

import os
from pathlib import Path

import pytest

from now_workbench.platform.config.origins import is_origin_allowed
from now_workbench.platform.config.paths import UnsafePathError, safe_child
from now_workbench.platform.config.settings import Settings


@pytest.mark.parametrize("name", ["sample-ai-assistant", "hr_onboarding.v2", "A1", "x" * 128])
def test_safe_child_accepts_plain_identifiers(tmp_path: Path, name: str) -> None:
    """Ordinary bundle ids resolve to a direct child of the root."""
    assert safe_child(tmp_path, name) == tmp_path.resolve() / name


@pytest.mark.parametrize(
    "name",
    [
        "",
        ".",
        "..",
        "../x",
        "a/b",
        "a\\b",
        "/etc",
        ".hidden",
        "a..b",
        "x" * 129,
        " space",
        "a\x00b",
    ],
)
def test_safe_child_rejects_unsafe_names(tmp_path: Path, name: str) -> None:
    """Empty, traversal, separator, hidden and oversized names are refused."""
    with pytest.raises(UnsafePathError):
        safe_child(tmp_path, name)


def test_safe_child_rejects_symlink_escaping_root(tmp_path: Path) -> None:
    """A child that is a symlink to another directory resolves outside the root and is refused."""
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "root"
    root.mkdir()
    os.symlink(outside, root / "evil")
    with pytest.raises(UnsafePathError, match="outside"):
        safe_child(root, "evil")


def test_unsafe_path_error_is_a_value_error() -> None:
    """Callers can map it with a plain ValueError handler (HTTP 400)."""
    assert issubclass(UnsafePathError, ValueError)


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:3000", "http://127.0.0.1:8080", "https://localhost", "http://[::1]:8080"],
)
def test_is_origin_allowed_accepts_loopback_origins(origin: str) -> None:
    """The default pattern admits the UI served from loopback on any port."""
    assert is_origin_allowed(origin, Settings().cors_origin_regex) is True


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.example",
        "http://localhost.evil.example",
        "http://127.0.0.1.evil.example",
        "http://evil.example/http://localhost",
        "null",
    ],
)
def test_is_origin_allowed_rejects_foreign_origins(origin: str) -> None:
    """Look-alike and unrelated origins are refused."""
    assert is_origin_allowed(origin, Settings().cors_origin_regex) is False


@pytest.mark.parametrize("origin", [None, ""])
def test_is_origin_allowed_missing_origin_is_non_browser_client(origin: str | None) -> None:
    """No Origin header means a CLI or test client, which is allowed."""
    assert is_origin_allowed(origin, Settings().cors_origin_regex) is True


def test_settings_default_host_is_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    """The unauthenticated API binds to loopback unless explicitly overridden."""
    monkeypatch.delenv("WORKBENCH_HOST", raising=False)
    assert Settings(_env_file=None).host == "127.0.0.1"


def test_settings_host_override_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Containers can still opt in to all interfaces through the environment."""
    monkeypatch.setenv("WORKBENCH_HOST", "0.0.0.0")
    assert Settings(_env_file=None).host == "0.0.0.0"
