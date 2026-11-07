# tests/test_domain_card_checks.py
# Domain-card checks: the dead-reference ratchet and the freshness nudge (STORY-068, STORY-069).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests for ADR-033's card checks, on tmp source trees and a real git repository."""

import importlib.util
import json
import subprocess
import sys
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


cards = _load(".ratchet/count_card_dead_references.py", "count_card_dead_references")
fresh = _load("scripts/hooks/check_domain_card_freshness.py", "check_domain_card_freshness")

SOURCE = '''
"""Module."""
import httpx
from now_workbench.platform.clock import utc_now
__all__ = ["make_widget", "WidgetRepository"]
LIMIT_DEFAULT = 3
class WidgetRepository:
    def __init__(self, conn, *, page_size=10):
        self.row_cache = {}
    def list_widgets(self): ...
def make_widget[T](spec: T) -> T:
    return {"code": "WIDGET_MISSING", "env": "WORKBENCH_WIDGET_DIR"}
DDL = "CREATE TABLE IF NOT EXISTS widget_rows (id INTEGER); CREATE INDEX idx_widget_rows ON x"
class WidgetSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKBENCH_")
    widget_limit: int = 3
class WidgetView(BaseModel):
    label: str
'''


@pytest.fixture
def src(tmp_path: Path) -> Path:
    """A miniature `src/now_workbench` with one domain and its card."""
    pkg = tmp_path / "src" / "now_workbench" / "domains" / "widgets"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(SOURCE)
    (pkg / "service_core.py").write_text("def helper_one(): ...\n")
    return tmp_path / "src" / "now_workbench"


def _card(src: Path, text: str) -> None:
    (src / "domains" / "widgets" / "CLAUDE.md").write_text(text)


# --------------------------------------------------------------------------- references


def test_references_reads_code_shaped_inline_spans_once_and_skips_fences() -> None:
    text = (
        "Use `WidgetRepository(conn)` and `make_widget()`, not `plain` or `Ok`.\n"
        "```python\nfrom x import `ghost_name`\n```\n"
        "See `service_core.py`, `widgets.list_widgets`, `make_widget` again, `/api/widgets`.\n"
        "Camel `listWidgets`, constant `LIMIT_DEFAULT`, short `Abc`.\n"
    )
    assert cards.references(text) == [
        (1, "WidgetRepository"),
        (1, "make_widget"),
        (5, "widgets.list_widgets"),
        (6, "listWidgets"),
        (6, "LIMIT_DEFAULT"),
    ]


def test_references_reads_the_leading_name_of_calls_subscripts_and_decorators() -> None:
    text = (
        "`GhostRepository(conn)` ``ghost_fn(1, 2)`` `Ghost_Box[T]` `@ghost_decorator`\n"
        "~~~\n`hidden_name`\n~~~\n"
        "`a_name, b_name` `GhostRepository | None` `POST /api/x` `git log --oneline`\n"
    )
    assert [name for _, name in cards.references(text)] == [
        "GhostRepository",
        "ghost_fn",
        "Ghost_Box",
        "ghost_decorator",
    ]


# --------------------------------------------------------------------------- defined names


def test_defined_names_covers_every_binding_kind(src: Path) -> None:
    names = cards.defined_names(src)
    expected = {
        "now_workbench",
        "domains",
        "widgets",
        "service_core",
        "helper_one",
        "WidgetRepository",
        "list_widgets",
        "page_size",
        "row_cache",
        "make_widget",
        "T",
        "LIMIT_DEFAULT",
        "WIDGET_MISSING",
        "WORKBENCH_WIDGET_DIR",
        "WORKBENCH_WIDGET_LIMIT",
        "widget_rows",
        "idx_widget_rows",
        "__init__",
        "utc_now",
        "clock",
        "platform",
        "httpx",
    }
    assert expected <= names
    assert "spec" in names and "conn" in names


# --------------------------------------------------------------------------- dead references


def test_dead_references_reports_only_names_src_does_not_define(src: Path, tmp_path: Path) -> None:
    _card(
        src,
        "# widgets\n"
        "- `WidgetRepository`, `widgets.make_widget`, `LIMIT_DEFAULT`\n"
        "- `fastapi.APIRouter`, `pathlib.Path`, `ValueError`\n"
        "- `GhostService` and `widgets.vanished_fn`\n"
        "- `WidgetRepository.list_widgets`, `WidgetRepository.make_widget`\n"
        "- `WidgetView.model_dump`\n",
    )
    dead = cards.dead_references(src, tmp_path / "none.txt")
    card = "src/now_workbench/domains/widgets/CLAUDE.md"
    assert dead == [
        f"{card}:4: GhostService",
        f"{card}:4: widgets.vanished_fn",
        f"{card}:5: WidgetRepository.make_widget",
    ]


def test_build_index_checks_project_modules_that_share_a_stdlib_name() -> None:
    """`platform` and `profile` are project modules, so a dead member under them is caught."""
    index = cards.build_index()
    assert index.resolves("platform.db.session.db_session")
    assert index.resolves("domains.profile.ProfileRepository")
    assert not index.resolves("platform.db.ghost_fn")
    assert not index.resolves("profile.ghost_fn")
    assert not index.resolves("ChatRepository.ghost_method")
    assert {"platform", "profile"} <= index.modules


def test_dead_references_honours_an_explained_allowlist_entry_only(
    src: Path, tmp_path: Path
) -> None:
    _card(src, "`GhostService` `Other_Name`\n")
    allow = tmp_path / "allow.txt"
    allow.write_text("# header\n\nGhostService  # an external API object\nOther_Name\n")
    assert cards.dead_references(src, allow) == [
        "allow.txt:4: 'Other_Name' has no '# reason'",
        "src/now_workbench/domains/widgets/CLAUDE.md:1: Other_Name",
    ]


def test_main_prints_each_error_and_the_count(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(cards, "dead_references", lambda: ["x:1: GhostService"])
    assert cards.main() == 0
    out = capsys.readouterr()
    assert out.out == "Violations: 1\n"
    assert out.err == "[ERROR] x:1: GhostService\n"


def test_shipped_cards_name_no_dead_identifier() -> None:
    """The real cards hold the ratchet's baseline of 0."""
    assert cards.dead_references() == []


def test_ratchet_registers_the_card_counter_at_zero() -> None:
    ratchet = (ROOT / ".ratchet" / "ratchet_check.py").read_text()
    assert '"card-dead-references"' in ratchet
    baselines = json.loads((ROOT / ".ratchet" / "baselines.json").read_text())
    assert baselines["counts"]["card-dead-references"] == 0


# --------------------------------------------------------------------------- freshness nudge


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repository with one domain card committed beside its code."""
    for var in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{var}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{var}_EMAIL", "test@example.com")
    monkeypatch.chdir(tmp_path)
    git("init", "-q", "-b", "main")
    git("config", "commit.gpgsign", "false")
    domain = Path("src/now_workbench/domains/widgets")
    domain.mkdir(parents=True)
    (domain / "CLAUDE.md").write_text("# widgets\n")
    (domain / "core.py").write_text("x = 0\n")
    git("add", ".")
    git("commit", "-q", "-m", "chore: card")
    return tmp_path


def _touch(path: str, n: int) -> None:
    for i in range(n):
        Path(path).write_text(f"x = {i + 1}\n")
        git("commit", "-q", "-am", f"chore: edit {i}")


def test_stale_cards_counts_commits_to_the_domain_since_the_card(repo: Path) -> None:
    _touch("src/now_workbench/domains/widgets/core.py", fresh.MAX_COMMITS - 1)
    assert fresh.stale_cards() == []
    _touch("src/now_workbench/domains/widgets/core.py", 1)
    [line] = fresh.stale_cards()
    assert line.startswith(
        f"src/now_workbench/domains/widgets/CLAUDE.md: {fresh.MAX_COMMITS} commits to "
        "src/now_workbench/domains/widgets and 0 days"
    )


def test_stale_cards_ignores_commits_outside_the_domain_and_names_old_cards(repo: Path) -> None:
    Path("README.md").write_text("x")
    git("add", "README.md")
    _touch("README.md", fresh.MAX_COMMITS)
    assert fresh.stale_cards() == []
    later = int(git("log", "-1", "--format=%ct").strip()) + fresh.MAX_DAYS * 86400
    [line] = fresh.stale_cards(now=later)
    assert f"0 commits to src/now_workbench/domains/widgets and {fresh.MAX_DAYS} days" in line


def test_stale_cards_skips_a_card_that_is_staged_but_never_committed(repo: Path) -> None:
    card = Path("src/now_workbench/domains/gadgets/CLAUDE.md")
    card.parent.mkdir(parents=True)
    card.write_text("# gadgets\n")
    git("add", str(card))
    assert fresh.stale_cards() == []


def test_main_stays_advisory_when_git_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)  # not a repository: every git call fails
    assert fresh.main() == 0
    assert "could not check the cards" in capsys.readouterr().out


def test_main_is_advisory_and_says_nothing_when_fresh(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert fresh.main() == 0
    assert capsys.readouterr().out == ""
    _touch("src/now_workbench/domains/widgets/core.py", fresh.MAX_COMMITS)
    assert fresh.main() == 0
    assert "may need a refresh" in capsys.readouterr().out
