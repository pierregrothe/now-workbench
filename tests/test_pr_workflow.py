# tests/test_pr_workflow.py
# The branch-and-PR workflow: guards, the gate stamp, review records, land and merge subjects.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests for STORY-066 (ADR-032), on real git repositories in tmp_path; `gh` is a fake script."""

import importlib.util
import json
import os
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


gate = _load("scripts/dev-tools/pr_gate.py", "pr_gate")
merge_msg = _load("scripts/hooks/prepare_merge_commit_msg.py", "prepare_merge_commit_msg")


def git(*args: str, cwd: Path | None = None) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _hooks_config(failing: set[str]) -> str:
    lines = ["repos:", "  - repo: local", "    hooks:"]
    for hook in gate.GATED:
        lines += [
            f"      - id: {hook}",
            f"        name: {hook}",
            f'        entry: "{"false" if hook in failing else "true"}"',
            "        language: system",
            "        pass_filenames: false",
            "        always_run: true",
            "        stages: [pre-push]",
        ]
    return "\n".join(lines) + "\n"


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repository with an `origin`, a commit on main and a story branch checked out."""
    for var in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{var}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{var}_EMAIL", "test@example.com")
    for var in ("PR_GATE_FORCE", "PRE_COMMIT_TO_REF", "PRE_COMMIT_REMOTE_BRANCH"):
        monkeypatch.delenv(var, raising=False)
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    git("init", "-q", "--bare", "-b", "main", str(origin))
    git("init", "-q", "-b", "main", str(work))
    monkeypatch.chdir(work)
    git("config", "commit.gpgsign", "false")
    git("remote", "add", "origin", str(origin))
    (work / ".pre-commit-config.yaml").write_text(_hooks_config(set()))
    git("add", ".")
    git("commit", "-q", "-m", "chore: start")
    git("push", "-q", "origin", "main")
    git("switch", "-q", "-c", "feature/x")
    return work


def _commit(name: str, text: str = "x") -> str:
    Path(name).parent.mkdir(parents=True, exist_ok=True)
    Path(name).write_text(text)
    git("add", name)
    git("commit", "-q", "-m", f"feat: {name}")
    return git("rev-parse", "HEAD")


def _stamp(sha: str, passed: bool = True) -> None:
    path = gate._stamp_path(sha)
    path.parent.mkdir(parents=True, exist_ok=True)
    checks = dict.fromkeys(gate.GATED, passed)
    path.write_text(json.dumps({"head": sha, "passed": passed, "checks": checks}))


# --------------------------------------------------------------------------- guards


def test_guard_branch_refuses_main_and_allows_a_story_branch(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert gate.guard_branch() == 0
    git("switch", "-q", "main")
    assert gate.guard_branch() == 1
    assert "no commits on main" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("remote", "code"), [("main", 1), ("refs/heads/main", 1), ("feature/x", 0), ("", 0)]
)
def test_guard_push_refuses_only_main(
    remote: str, code: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PRE_COMMIT_REMOTE_BRANCH", remote)
    assert gate.guard_push() == code


# --------------------------------------------------------------------------- check and the stamp


def test_check_stamps_a_pass_and_the_push_skips_the_proven_checks(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    head = _commit("a.txt")
    assert gate.check() == 0
    stamp = gate.read_stamp(head)
    assert stamp is not None
    assert stamp["passed"] is True
    assert stamp["checks"] == dict.fromkeys(gate.GATED, True)
    monkeypatch.setenv("PRE_COMMIT_TO_REF", head)
    assert gate.run_unless_proven("web-e2e", ["false"]) == 0
    assert "web-e2e: skipped -- proven by pr_gate check" in capsys.readouterr().out
    assert gate.main(["status"]) == 0


def test_check_stamps_a_failure_and_nothing_is_skipped(repo: Path) -> None:
    Path(".pre-commit-config.yaml").write_text(_hooks_config({"mutation-gate"}))
    _commit("b.txt")
    git("commit", "-q", "-am", "chore: failing gate")
    head = git("rev-parse", "HEAD")
    assert gate.check() == 1
    stamp = gate.read_stamp(head)
    assert stamp is not None
    assert stamp["passed"] is False
    assert stamp["checks"] == {**dict.fromkeys(gate.GATED, True), "mutation-gate": False}
    assert gate.skip_reason("pytest-pre-push") is None
    assert gate.run_unless_proven("mutation-gate", ["false"]) == 1


def test_check_refuses_a_dirty_tree_and_main(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    head = _commit("c.txt")
    Path("c.txt").write_text("edited")
    assert gate.check() == 1
    assert gate.read_stamp(head) is None
    git("checkout", "--", "c.txt")
    git("switch", "-q", "main")
    assert gate.check() == 1
    assert "refusing to check main" in capsys.readouterr().out
    assert gate.main(["status"]) == 1


@pytest.mark.parametrize(
    "case", ["other-commit", "unset-ref", "dirty", "no-stamp", "forced", "failed"]
)
def test_skip_reason_runs_the_check_unless_the_exact_commit_is_proven(
    case: str, repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _commit("d.txt")
    head = _commit("e.txt")
    _stamp(head, passed=case != "failed")
    monkeypatch.setenv("PRE_COMMIT_TO_REF", head)
    match case:
        case "other-commit":
            monkeypatch.setenv("PRE_COMMIT_TO_REF", first)
        case "unset-ref":
            monkeypatch.delenv("PRE_COMMIT_TO_REF")
        case "dirty":
            Path("e.txt").write_text("edited")
        case "no-stamp":
            gate._stamp_path(head).unlink()
        case "forced":
            monkeypatch.setenv("PR_GATE_FORCE", "1")
    assert gate.skip_reason("pytest-pre-push") is None
    marker = repo.parent / "ran"
    assert gate.run_unless_proven("pytest-pre-push", ["touch", str(marker)]) == 0
    assert marker.exists()


def test_skip_reason_skips_the_proven_commit_being_pushed(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = _commit("e2.txt")
    _stamp(head)
    monkeypatch.setenv("PRE_COMMIT_TO_REF", head)
    marker = repo.parent / "ran"
    assert gate.run_unless_proven("pytest-pre-push", ["touch", str(marker)]) == 0
    assert not marker.exists()


def test_read_stamp_ignores_a_stamp_for_another_commit_or_garbage(repo: Path) -> None:
    head = _commit("f.txt")
    path = gate._stamp_path(head)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"head": "0" * 40, "passed": True}))
    assert gate.read_stamp(head) is None
    path.write_text("{not json")
    assert gate.read_stamp(head) is None


def test_main_run_unless_proven_needs_a_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert gate.main(["run-unless-proven", "web-e2e", "--"]) == 2
    assert "no command" in capsys.readouterr().out


# --------------------------------------------------------------------------- review record and land


def test_review_record_path_turns_slashes_into_dashes() -> None:
    record = gate.review_record("feature/pr-workflow")
    assert record == Path(".primer/reviews/feature-pr-workflow.md")


def _record(head: str) -> str:
    return _commit(".primer/reviews/feature-x.md", f"# Review record\n\n- Head: {head}\n")


def test_record_covers_needs_a_committed_record_naming_an_ancestor(repo: Path) -> None:
    reviewed = _commit("g.txt")
    assert "no review record" in str(gate._record_covers("feature/x", reviewed))
    head = _record(reviewed)
    assert gate._record_covers("feature/x", head) is None
    git("switch", "-q", "main")
    other = _commit("h.txt")
    git("switch", "-q", "feature/x")
    stale = _record(other)
    assert "re-review" in str(gate._record_covers("feature/x", stale))


def test_record_covers_refuses_a_head_already_on_main(repo: Path) -> None:
    """A record naming main's tip (an ancestor of every branch) reviews nothing."""
    _commit("m.txt")
    head = _record(git("rev-parse", "origin/main"))
    assert "re-review" in str(gate._record_covers("feature/x", head))


def test_record_covers_ignores_a_head_mentioned_in_prose(repo: Path) -> None:
    reviewed = _commit("n.txt")
    head = _commit(".primer/reviews/feature-x.md", f"Notes: the old Head: {reviewed} was fine\n")
    assert "re-review" in str(gate._record_covers("feature/x", head))


def _fake_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, view: dict[str, str]) -> Path:
    """Put a fake `gh` first on PATH; it answers `pr view` and `run list` and logs every call."""
    bin_dir, log = tmp_path / "bin", tmp_path / "gh.log"
    bin_dir.mkdir()
    run = {
        "databaseId": 7,
        "headBranch": "feature/x",
        "status": "completed",
        "conclusion": "success",
        "createdAt": "9999-01-01T00:00:00Z",
    }
    script = bin_dir / "gh"
    script.write_text(
        "#!/bin/sh\n"
        f'echo "$*" >> "{log}"\n'
        'case "$1 $2" in\n'
        f"  'pr view') echo '{json.dumps(view)}' ;;\n"
        f"  'run list') echo '{json.dumps([run])}' ;;\n"
        "esac\n"
    )
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    return log


def _view(head: str, state: str = "OPEN", base: str = "main") -> dict[str, str]:
    return {"state": state, "baseRefName": base, "headRefName": "feature/x", "headRefOid": head}


def test_land_merges_a_proven_reviewed_head_and_returns_to_main(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = _record(_commit("i.txt"))
    _stamp(head)
    log = _fake_gh(tmp_path, monkeypatch, _view(head))
    assert gate.main(["land", "5", "--wait", "0", "--poll", "0"]) == 0
    calls = log.read_text()
    assert f"pr merge 5 --squash --delete-branch --match-head-commit {head}" in calls
    assert "run list --workflow release.yml" in calls
    assert git("branch", "--show-current") == "main"


@pytest.mark.parametrize("case", ["closed", "other-base", "no-stamp", "failed-stamp", "no-record"])
def test_land_refuses_and_merges_nothing(
    case: str, repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    head = _commit("j.txt") if case == "no-record" else _record(_commit("j.txt"))
    if case != "no-stamp":
        _stamp(head, passed=case != "failed-stamp")
    state = "MERGED" if case == "closed" else "OPEN"
    log = _fake_gh(
        tmp_path, monkeypatch, _view(head, state, "dev" if case == "other-base" else "main")
    )
    assert gate.land(5, wait=0, poll=0) == 1
    assert "pr merge" not in log.read_text()
    assert git("branch", "--show-current") == "feature/x"


def test_await_release_gives_up_when_no_run_appears(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _fake_gh(tmp_path, monkeypatch, _view("0" * 40))
    gate._await_release("feature/other", "2026-01-01T00:00:00Z", wait=0, poll=0)
    assert "did not finish in time" in capsys.readouterr().out


# ---------------------------------------------------------------- merge subjects and wiring


def test_rewrite_merge_subject_conventionalizes_only_default_merge_subjects() -> None:
    msg = "Merge branch 'main' into feature/x\n\nbody\n"
    assert merge_msg.rewrite_merge_subject(msg) == f"chore(merge): {msg}"
    assert merge_msg.rewrite_merge_subject("feat: merge things\n") is None
    assert merge_msg.rewrite_merge_subject("") is None


def test_main_rewrites_the_message_file_of_a_real_merge(repo: Path) -> None:
    _commit("k.txt")
    git("switch", "-q", "main")
    _commit("l.txt")
    git("switch", "-q", "feature/x")
    git("merge", "--no-ff", "--no-commit", "main")
    msg = Path(".git/COMMIT_EDITMSG")
    msg.write_text("Merge branch 'main' into feature/x\n")
    assert merge_msg.main([str(msg)]) == 0
    assert msg.read_text() == "chore(merge): Merge branch 'main' into feature/x\n"


def test_main_leaves_a_normal_commit_message_alone(repo: Path) -> None:
    msg = Path(".git/COMMIT_EDITMSG")
    msg.write_text("Merge is the wrong word for a normal commit\n")
    assert merge_msg.main([str(msg), "message"]) == 0
    assert msg.read_text().startswith("Merge is")
    assert merge_msg.main([]) == 0
    assert merge_msg.main([str(Path("missing"))]) == 0


def test_pre_commit_config_wraps_every_gated_check_and_wires_the_guards() -> None:
    config = (ROOT / ".pre-commit-config.yaml").read_text()
    for hook in gate.GATED:
        assert f"pr_gate.py run-unless-proven {hook} -- " in config
    for hook in ("guard-branch", "guard-push", "conventionalize-merge-msg"):
        assert f"- id: {hook}" in config
    assert "prepare-commit-msg" in config.split("repos:")[0]
