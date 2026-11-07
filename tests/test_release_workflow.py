# tests/test_release_workflow.py
# Releases mark a delivered epic: the release gate, the version bump and the changelog contract.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests for STORY-067 (ADR-032), on a real git repository in tmp_path."""

import importlib.util
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gate = _load("scripts/dev-tools/release_gate.py", "release_gate")
changelog = _load("scripts/dev-tools/primer_changelog.py", "primer_changelog")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repository holding one complete epic and one in progress."""
    for var in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{var}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{var}_EMAIL", "test@example.com")
    monkeypatch.chdir(tmp_path)
    git("init", "-q", "-b", "main")
    git("config", "commit.gpgsign", "false")
    _epic("2026.11a-done", "Progress: 7/7 stories done -- COMPLETE")
    _epic("2026.11c-open", "Progress: 1/2 stories done")
    return tmp_path


def _epic(name: str, progress: str) -> str:
    path = Path(".primer/epics") / name / "epic.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# Epic: {name}\n\nBoard: EPIC-1\n{progress}\n")
    git("add", ".")
    git("commit", "-q", "-m", f"chore: {name}")
    return git("rev-parse", "HEAD")


@pytest.mark.parametrize(
    ("text", "complete"),
    [
        ("Progress: 2/2 stories done", True),
        ("Progress: 7/7 stories done -- COMPLETE", True),
        ("Status: complete", True),
        ("Status: done", True),
        ("Progress: 1/2 stories done", False),
        ("Progress: 0/0 stories done", False),
        ("Status: in-progress\nProgress: 0/5 stories done", False),
        ("no progress line", False),
    ],
)
def test_is_complete_reads_the_progress_and_status_lines(text: str, complete: bool) -> None:
    assert gate.is_complete(text) is complete


def test_decide_releases_when_a_merge_closes_an_epic(repo: Path) -> None:
    sha = _epic("2026.11c-open", "Progress: 2/2 stories done")
    assert gate.decide(sha, set()) == {"release": "true", "reason": "closes 2026.11c-open"}


def test_decide_does_not_release_an_edit_to_a_closed_epic(repo: Path) -> None:
    sha = _epic("2026.11a-done", "Progress: 7/7 stories done -- COMPLETE (edited)")
    assert gate.decide(sha, set())["release"] == "false"


def test_decide_releases_for_the_release_label_only(repo: Path) -> None:
    sha = _epic("2026.11c-open", "Progress: 1/2 stories done (note)")
    assert gate.decide(sha, {"release"}) == {"release": "true", "reason": "release label"}
    assert gate.decide(sha, {"bug"}) == {
        "release": "false",
        "reason": "no epic closed, no release label",
    }


def test_main_decide_writes_the_github_output(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sha = _epic("2026.11c-open", "Progress: 2/2 stories done")
    out = tmp_path / "gh-output"
    assert gate.main(["decide", sha, "--labels", " release, ux ", "--github-output", str(out)]) == 0
    assert out.read_text() == "release=true\nreason=closes 2026.11c-open\n"
    assert "release=true" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("version", "today", "new"),
    [
        ("0.1.0", date(2026, 11, 7), "2026.11.0"),
        ("2026.11.0", date(2026, 11, 30), "2026.11.1"),
        ("2026.11.9", date(2026, 11, 30), "2026.11.10"),
        ("2026.11.4", date(2026, 12, 1), "2026.12.0"),
        ("2025.11.4", date(2026, 11, 1), "2026.11.0"),
    ],
)
def test_bumped_counts_releases_within_a_utc_month(version: str, today: date, new: str) -> None:
    assert gate.bumped(version, today) == new


def test_bump_writes_pyproject_and_both_web_package_files(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "2026.11.0"\n\n[tool.x]\nversion = "9.9.9"\n'
    )
    web = tmp_path / "web"
    web.mkdir()
    (web / "package.json").write_text(json.dumps({"name": "w", "version": "2026.11.0"}))
    lock = {"version": "0.1.0", "packages": {"": {"version": "0.1.0"}, "node_modules/a": {}}}
    (web / "package-lock.json").write_text(json.dumps(lock))
    assert gate.bump(tmp_path, date(2026, 11, 7)) == "2026.11.1"
    assert 'version = "2026.11.1"' in (tmp_path / "pyproject.toml").read_text()
    assert 'version = "9.9.9"' in (tmp_path / "pyproject.toml").read_text()
    assert json.loads((web / "package.json").read_text())["version"] == "2026.11.1"
    locked = json.loads((web / "package-lock.json").read_text())
    assert locked["version"] == locked["packages"][""]["version"] == "2026.11.1"


def test_main_bump_prints_the_new_version(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n')
    monkeypatch.chdir(tmp_path)
    assert gate.main(["bump"]) == 0
    assert re.fullmatch(r"\d{4}\.\d{2}\.0\n", capsys.readouterr().out)


def test_changelog_roll_accepts_the_bumped_version(tmp_path: Path) -> None:
    """The engine that rolls the changelog takes the version bump produces."""
    (tmp_path / "CHANGELOG.md").write_text((ROOT / "CHANGELOG.md").read_text())
    version = gate.bumped("0.1.0", date(2026, 11, 7))
    root = ["--root", str(tmp_path)]
    assert changelog.main(["roll", version, "--allow-empty", "--date", "2026-11-07", *root]) == 0
    assert f"## [{version}] - 2026-11-07" in (tmp_path / "CHANGELOG.md").read_text()
    assert changelog.main(["validate", *root]) == 0


def test_bump_refuses_a_pyproject_without_a_version(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
    with pytest.raises(ValueError, match="no version line"):
        gate.bump(tmp_path, date(2026, 11, 7))


def test_bump_matches_the_shipped_version_files() -> None:
    """The real files carry the versions bump rewrites, and they agree."""
    version = gate._PYPROJECT_VERSION.search((ROOT / "pyproject.toml").read_text())
    assert version is not None
    for name in ("package.json", "package-lock.json"):
        assert json.loads((ROOT / "web" / name).read_text())["version"] == version.group(2)


def test_changelog_meets_the_primer_contract() -> None:
    """CHANGELOG.md: one line per entry, at most 160 characters, an [Unreleased] block."""
    assert changelog.main(["validate", "--root", str(ROOT)]) == 0


def test_changelog_engine_is_the_primer_template() -> None:
    """The vendored engine stays byte-identical to the skill's template when it is installed."""
    template = Path.home() / ".claude/skills/primer/reference/templates/primer-changelog.py"
    if not template.exists():
        pytest.skip("primer skill not installed on this machine")
    assert (ROOT / "scripts/dev-tools/primer_changelog.py").read_bytes() == template.read_bytes()
