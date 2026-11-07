# scripts/dev-tools/pr_gate.py
# The branch-and-PR workflow: branch guards, the once-per-PR gate stamp, and land (ADR-032).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Work reaches ``main`` only through a pull request whose head the full gate proved.

Commands::

    pr_gate.py check                        run the gated pre-push checks once, stamp HEAD
    pr_gate.py status                       print the stamp for HEAD, if any
    pr_gate.py run-unless-proven ID -- CMD  pre-push wrapper: skip CMD when a stamp proves it
    pr_gate.py guard-branch                 pre-commit: refuse a commit on main
    pr_gate.py guard-push                   pre-push: refuse a push to main
    pr_gate.py land PR [--wait S]           squash-merge a proven, reviewed PR; bring main current

A stamp is ``<git-common-dir>/pr-gate-stamps/<sha>.json``: ``head``, ``passed``, ``checks``
(each gated check id and whether it passed) and ``recorded_at``. ``check`` writes one only when
the tracked tree was clean and HEAD did not move while it ran, so the stamp describes exactly
that commit. ``run-unless-proven`` skips its command only when the commit being pushed is HEAD,
the tracked tree is clean and a stamp for it records that check as passed; anything else -- no
stamp, a failure, another commit, local edits -- runs the command.

``land`` refuses a PR unless its head has a passing stamp and the branch's review record
(``.primer/reviews/<branch-with-dashes>.md``, line ``Head: <sha>``) covers an ancestor of the
head. It then squash-merges, waits for the release workflow's run on that merge, switches to
``main`` and fast-forwards it, so local ``main`` never sits behind the bot's release commit.

Exit codes: 0 done, 1 refused or a check failed, 2 usage error.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

__all__ = [
    "GATED",
    "MAIN",
    "Stamp",
    "check",
    "guard_branch",
    "guard_push",
    "land",
    "main",
    "review_record",
    "run_unless_proven",
    "skip_reason",
]

MAIN = "main"
# The pre-push hooks the stamp can stand in for (ids in .pre-commit-config.yaml).
GATED = ("pytest-pre-push", "mutation-gate", "web-e2e")
FORCE_ENV = "PR_GATE_FORCE"
RELEASE_WORKFLOW = "release.yml"

type Stamp = dict[str, object]


def _git(*args: str, cwd: Path | None = None) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _head() -> str:
    return _git("rev-parse", "HEAD")


def _branch() -> str:
    return _git("branch", "--show-current")


def _tracked_changes() -> str:
    return _git("status", "--porcelain", "--untracked-files=no")


def _stamp_path(sha: str) -> Path:
    common = Path(_git("rev-parse", "--git-common-dir")).resolve()
    return common / "pr-gate-stamps" / f"{sha}.json"


def read_stamp(sha: str) -> Stamp | None:
    """Return the stamp recorded for a commit, or None when there is none or it is unreadable.

    Args:
        sha: Full commit id.

    Returns:
        The stamp document, or None.
    """
    try:
        data = json.loads(_stamp_path(sha).read_text())
    except OSError, ValueError:
        return None
    return data if isinstance(data, dict) and data.get("head") == sha else None


def _proved(stamp: Stamp | None, ids: tuple[str, ...]) -> bool:
    if stamp is None or stamp.get("passed") is not True:
        return False
    checks = stamp.get("checks")
    return isinstance(checks, dict) and all(checks.get(i) is True for i in ids)


def check() -> int:
    """Run every gated check once on HEAD and stamp the verdict.

    Returns:
        0 when every check passed, 1 otherwise (or when the tree was not stampable).
    """
    if _branch() == MAIN:
        print(f"pr_gate: refusing to check {MAIN}; run it on the story's branch.")
        return 1
    head, before = _head(), _tracked_changes()
    if before:
        print("pr_gate: the tracked tree has changes; commit them first (nothing stamped).")
        return 1
    results: dict[str, bool] = {}
    env = {**os.environ, FORCE_ENV: "1"}
    for hook in GATED:
        print(f"pr_gate: running {hook} ...", flush=True)
        cmd = ["pre-commit", "run", hook, "--hook-stage", "pre-push", "--all-files"]
        results[hook] = subprocess.run(cmd, env=env, check=False).returncode == 0
    if _head() != head or _tracked_changes() != before:
        print("pr_gate: HEAD or the tracked tree changed during the run (nothing stamped).")
        return 1
    passed = all(results.values())
    stamp = {
        "head": head,
        "passed": passed,
        "checks": results,
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    path = _stamp_path(head)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stamp, indent=2) + "\n")
    failed = [k for k, ok in results.items() if not ok]
    verdict = "PASS" if passed else f"FAIL ({', '.join(failed)})"
    print(f"pr_gate: {verdict} stamped for {head[:12]}")
    return 0 if passed else 1


def status() -> int:
    """Print the stamp for HEAD.

    Returns:
        0 when HEAD has a passing stamp, 1 otherwise.
    """
    head = _head()
    stamp = read_stamp(head)
    if stamp is None:
        print(f"pr_gate: no stamp for {head[:12]}; run pr_gate.py check")
        return 1
    print(json.dumps(stamp, indent=2))
    return 0 if _proved(stamp, GATED) else 1


def skip_reason(hook: str) -> str | None:
    """Say why a pre-push check may be skipped, or None when it must run.

    Args:
        hook: The gated hook id.

    Returns:
        A one-line reason to skip, or None.
    """
    if os.environ.get(FORCE_ENV):
        return None
    head = _head()
    pushed = os.environ.get("PRE_COMMIT_TO_REF", "")
    if pushed and pushed != head:
        return None
    if _tracked_changes():
        return None
    stamp = read_stamp(head)
    if not _proved(stamp, (hook,)):
        return None
    assert stamp is not None
    return f"proven by pr_gate check at {stamp.get('recorded_at')} on {head[:12]}"


def run_unless_proven(hook: str, cmd: list[str]) -> int:
    """Run a gated pre-push command unless a stamp proves it passed on this exact commit.

    Args:
        hook: The gated hook id.
        cmd: The command to run.

    Returns:
        The command's exit code, or 0 when skipped.
    """
    reason = skip_reason(hook)
    if reason is not None:
        print(f"{hook}: skipped -- {reason}")
        return 0
    return subprocess.run(cmd, check=False).returncode


def guard_branch() -> int:
    """Refuse a commit on main (a merge commit during a conflict is a commit too).

    Returns:
        0 on a story branch, 1 on main.
    """
    if _branch() != MAIN:
        return 0
    print(
        f"guard-branch: no commits on {MAIN}. Work on a story branch "
        "(git switch -c feature/<slug>), then open a PR and land it with pr_gate.py land."
    )
    return 1


def guard_push() -> int:
    """Refuse a push whose remote branch is main (pre-commit exports it).

    Returns:
        0 for any other branch, 1 for main.
    """
    remote = os.environ.get("PRE_COMMIT_REMOTE_BRANCH", "")
    if remote not in {MAIN, f"refs/heads/{MAIN}"}:
        return 0
    print(f"guard-push: {MAIN} only changes through a merged PR (pr_gate.py land <pr>).")
    return 1


def review_record(branch: str) -> Path:
    """Return the review record path for a branch (slashes become dashes).

    Args:
        branch: Branch name.

    Returns:
        The path, relative to the repository root.
    """
    return Path(".primer") / "reviews" / f"{branch.replace('/', '-')}.md"


def _record_covers(branch: str, head: str) -> str | None:
    rel = review_record(branch).as_posix()
    try:
        text = _git("show", f"{head}:{rel}")
    except subprocess.CalledProcessError:
        return f"no review record {rel} at the PR head"
    for sha in re.findall(r"Head: ([0-9a-f]{9,64})", text):
        ok = subprocess.run(["git", "merge-base", "--is-ancestor", sha, head], check=False)
        if ok.returncode == 0:
            return None
    return f"{rel} names no Head that is an ancestor of {head[:12]}; re-review"


def _gh_json(*args: str) -> object:
    return json.loads(
        subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout
    )


def _release_run(branch: str, since: str) -> dict[str, object] | None:
    fields = "databaseId,headBranch,status,conclusion,createdAt"
    runs = _gh_json(
        "run", "list", "--workflow", RELEASE_WORKFLOW, "--limit", "20", "--json", fields
    )
    assert isinstance(runs, list)
    mine = [r for r in runs if r.get("headBranch") == branch and r.get("createdAt", "") >= since]
    return mine[0] if mine else None


def _await_release(branch: str, since: str, wait: float, poll: float) -> None:
    deadline = time.monotonic() + wait
    while True:
        run = _release_run(branch, since)
        if run is not None and run.get("status") == "completed":
            print(f"land: release run {run.get('databaseId')} {run.get('conclusion')}")
            return
        if time.monotonic() >= deadline:
            print("land: the release run did not finish in time; main may move again shortly.")
            return
        time.sleep(poll)


def land(pr: int, wait: float, poll: float) -> int:
    """Squash-merge a PR whose head is proven and reviewed, then bring main current.

    Args:
        pr: Pull request number.
        wait: Seconds to wait for the release run.
        poll: Seconds between polls.

    Returns:
        0 when merged and main is current, 1 when refused.
    """
    info = _gh_json("pr", "view", str(pr), "--json", "state,baseRefName,headRefName,headRefOid")
    assert isinstance(info, dict)
    head, branch = str(info["headRefOid"]), str(info["headRefName"])
    if info["state"] != "OPEN" or info["baseRefName"] != MAIN:
        print(f"land: PR #{pr} is {info['state']} against {info['baseRefName']}; nothing merged.")
        return 1
    _git("fetch", "--quiet", "origin")
    if not _proved(read_stamp(head), GATED):
        print(f"land: {head[:12]} has no passing stamp; run pr_gate.py check, push, then land.")
        return 1
    problem = _record_covers(branch, head)
    if problem is not None:
        print(f"land: {problem}.")
        return 1
    since = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    subprocess.run(
        ["gh", "pr", "merge", str(pr), "--squash", "--delete-branch", "--match-head-commit", head],
        check=True,
    )
    _await_release(branch, since, wait, poll)
    if _branch() != MAIN:
        _git("switch", MAIN)
    _git("pull", "--ff-only", "--quiet", "origin", MAIN)
    print(f"land: PR #{pr} merged; {MAIN} is at {_head()[:12]}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    sub.add_parser("status")
    sub.add_parser("guard-branch")
    sub.add_parser("guard-push")
    run = sub.add_parser("run-unless-proven")
    run.add_argument("hook", choices=GATED)
    run.add_argument("cmd", nargs=argparse.REMAINDER)
    lnd = sub.add_parser("land")
    lnd.add_argument("pr", type=int)
    lnd.add_argument("--wait", type=float, default=300.0)
    lnd.add_argument("--poll", type=float, default=10.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Dispatch a command.

    Args:
        argv: Arguments (defaults to sys.argv[1:]).

    Returns:
        The process exit code.
    """
    args = _parser().parse_args(argv)
    match args.command:
        case "check":
            return check()
        case "status":
            return status()
        case "guard-branch":
            return guard_branch()
        case "guard-push":
            return guard_push()
        case "run-unless-proven":
            cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
            if not cmd:
                print("run-unless-proven: no command after --")
                return 2
            return run_unless_proven(args.hook, cmd)
        case _:
            return land(args.pr, args.wait, args.poll)


if __name__ == "__main__":
    sys.exit(main())
