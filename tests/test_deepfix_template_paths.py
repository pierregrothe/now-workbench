# tests/test_deepfix_template_paths.py
# Regression tests: template instantiation must confine and validate the target bundle id
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for path safety in TemplateEngine.instantiate."""

from pathlib import Path

import pytest

from now_workbench.domains.templates.engine import TemplateEngine
from now_workbench.domains.templates.models import TemplateInstantiationRequest
from now_workbench.platform.config.paths import UnsafePathError


def _setup(tmp_path: Path) -> tuple[TemplateEngine, Path, Path]:
    bundles = tmp_path / "bundles"
    base = bundles / "base"
    base.mkdir(parents=True)
    (base / "a.txt").write_text("{{customer_name}}", encoding="utf-8")
    sentinel = tmp_path / "sentinel"
    sentinel.mkdir()
    (sentinel / "keep.txt").write_text("keep", encoding="utf-8")
    return TemplateEngine(bundles_dir=bundles, output_dir=bundles), base, sentinel


def _req(target: str) -> TemplateInstantiationRequest:
    return TemplateInstantiationRequest(target_bundle_id=target, customer_name="Acme")


@pytest.mark.parametrize("bad", ["..", "../sentinel", "a/b", "", "/tmp"])
def test_instantiate_traversal_id_rejected_and_nothing_deleted(tmp_path: Path, bad: str) -> None:
    engine, conn, sentinel = _setup(tmp_path)
    with pytest.raises(UnsafePathError):
        engine.instantiate("base", _req(bad))
    assert (sentinel / "keep.txt").exists()
    assert (conn / "a.txt").exists()


def test_instantiate_target_equals_base_rejected_and_base_kept(tmp_path: Path) -> None:
    engine, conn, _ = _setup(tmp_path)
    with pytest.raises(UnsafePathError):
        engine.instantiate("base", _req("base"))
    assert (conn / "a.txt").read_text(encoding="utf-8") == "{{customer_name}}"


def test_instantiate_valid_id_creates_bundle(tmp_path: Path) -> None:
    engine, conn, _ = _setup(tmp_path)
    out = engine.instantiate("base", _req("acme-demo"))
    assert (out / "a.txt").read_text(encoding="utf-8") == "Acme"
