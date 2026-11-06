# tests/test_deepfix_ratchet_fail_closed.py
# Regression tests: the ratchet must fail closed on bad or incomplete baselines.
# Author: Pierre Grothe
# Date: 2026-11-06
"""The ratchet must never pass when its baselines are unreadable or missing."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / ".ratchet" / "ratchet_check.py"

__all__: list[str] = []


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ratchet_check_under_test", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def ratchet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    module = _load_module()
    monkeypatch.setattr(module, "BASELINES_FILE", tmp_path / "baselines.json")
    monkeypatch.setitem(module.VALIDATORS, "no-mocks", {"cmd": ["true"], "description": "fake"})
    monkeypatch.setattr(module, "_count_violations", lambda cmd: 5)
    return module


def test_load_baselines_corrupt_json_raises(ratchet: ModuleType) -> None:
    ratchet.BASELINES_FILE.write_text("{<<<<<<< not json", encoding="utf-8")
    with pytest.raises(ratchet.BaselinesError):
        ratchet._load_baselines()


def test_load_baselines_missing_file_raises(ratchet: ModuleType) -> None:
    with pytest.raises(ratchet.BaselinesError):
        ratchet._load_baselines()


def test_load_baselines_wrong_shape_raises(ratchet: ModuleType) -> None:
    ratchet.BASELINES_FILE.write_text(json.dumps({"counts": {"no-mocks": "x"}}), encoding="utf-8")
    with pytest.raises(ratchet.BaselinesError):
        ratchet._load_baselines()


def test_check_validator_corrupt_baselines_fails(ratchet: ModuleType) -> None:
    ratchet.BASELINES_FILE.write_text("garbage", encoding="utf-8")
    passed, _, _ = ratchet.check_validator("no-mocks")
    assert passed is False


def test_check_validator_missing_entry_fails(ratchet: ModuleType) -> None:
    ratchet.BASELINES_FILE.write_text(json.dumps({"counts": {}}), encoding="utf-8")
    passed, _, _ = ratchet.check_validator("no-mocks")
    assert passed is False


def test_check_validator_missing_entry_does_not_create_baseline(ratchet: ModuleType) -> None:
    ratchet.BASELINES_FILE.write_text(json.dumps({"counts": {}}), encoding="utf-8")
    ratchet.check_validator("no-mocks", write=True)
    assert json.loads(ratchet.BASELINES_FILE.read_text(encoding="utf-8"))["counts"] == {}


def test_check_validator_corrupt_baselines_not_overwritten_on_write(ratchet: ModuleType) -> None:
    ratchet.BASELINES_FILE.write_text("garbage", encoding="utf-8")
    ratchet.check_validator("no-mocks", write=True)
    assert ratchet.BASELINES_FILE.read_text(encoding="utf-8") == "garbage"


def test_check_validator_valid_baseline_at_count_passes(ratchet: ModuleType) -> None:
    ratchet.BASELINES_FILE.write_text(json.dumps({"counts": {"no-mocks": 5}}), encoding="utf-8")
    passed, current, baseline = ratchet.check_validator("no-mocks")
    assert (passed, current, baseline) == (True, 5, 5)
