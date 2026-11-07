# scripts/dev-tools/release_gate.py
# Decide whether a squash merge to main cuts a release, and bump the version when it does.
# Author: Pierre Grothe
# Date: 2026-11-07
"""A release marks a shipped PRD, not every merge (ADR-032).

A merge is a release when EITHER it flips some ``.primer/prd/PRD-*.md`` to shipped (its
front-matter ``status:`` reads ``shipped`` after the merge and did not before -- what
``/primer prd ship`` writes), OR the pull request carries the ``release`` label (a hotfix).
Closing an epic no longer releases on its own: an epic is a slice of work, a PRD is the
product commitment a release delivers (owner, 2026-11-07). Versions are CalVer, ``YYYY.MM.N``
(the primer changelog engine's scheme): N counts the releases of a UTC month from 0. Comparing
before with after means editing a PRD that already shipped never releases again.

Commands::

    release_gate.py decide <merge-sha> [--labels a,b] [--github-output FILE]
    release_gate.py bump                 # pyproject.toml, web/package.json, web/package-lock.json

``decide`` prints ``release=`` and ``reason=`` lines (appended to the GitHub
output file when given) and always exits 0: the decision is the output. ``bump`` prints the new
version. Exit code 2 on a usage error.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path

__all__ = ["bump", "bumped", "decide", "is_shipped", "main", "shipped_prds"]

# Tolerant of CRLF, a leading BOM, quoted values and a trailing comment, so an unusual PRD file
# never silently skips a release.
_FRONT_MATTER = re.compile(r"\A\ufeff?---\r?\n(.*?)\r?\n---\r?$", re.S | re.M)
_STATUS = re.compile(r"^status:\s*[\"']?([A-Za-z-]+)[\"']?\s*(?:#.*)?\r?$", re.M)
_PYPROJECT_VERSION = re.compile(r'^(version\s*=\s*")([^"]+)(")', re.M)


def is_shipped(prd_md: str) -> bool:
    """Say whether a PRD's front matter marks it shipped.

    Args:
        prd_md: The text of a ``PRD-*.md``.

    Returns:
        True when the front matter's ``status:`` is ``shipped``.
    """
    front = _FRONT_MATTER.match(prd_md)
    status = _STATUS.search(front.group(1)) if front else None
    return status is not None and status.group(1).lower() == "shipped"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def shipped_prds(rev: str) -> set[str]:
    """List the PRDs marked shipped at a revision.

    Args:
        rev: Any git revision.

    Returns:
        The file stems (``PRD-004-otto-memory``) of the shipped PRDs there.
    """
    try:
        listing = _git("ls-tree", "-r", "-z", "--name-only", rev, "--", ".primer/prd")
    except subprocess.CalledProcessError:
        return set()  # no such revision: the parent of a root commit
    names = [name for name in listing.split("\0") if name]
    return {
        Path(name).stem
        for name in names
        if Path(name).name.startswith("PRD-")
        and name.endswith(".md")
        and is_shipped(_git("show", f"{rev}:{name}"))
    }


def decide(sha: str, labels: set[str]) -> dict[str, str]:
    """Decide whether a squash merge is a release.

    Args:
        sha: The merge commit (its parent is main before the merge).
        labels: The pull request's labels.

    Returns:
        ``release`` (true/false) and ``reason``.
    """
    shipped = sorted(shipped_prds(sha) - shipped_prds(f"{sha}^"))
    if shipped:
        return {"release": "true", "reason": f"ships {', '.join(shipped)}"}
    if "release" in labels:
        return {"release": "true", "reason": "release label"}
    return {"release": "false", "reason": "no PRD shipped, no release label"}


def bumped(version: str, today: date) -> str:
    """Return the next CalVer version.

    Args:
        version: The current version (``YYYY.MM.N``, or any other scheme before the first).
        today: The release date (UTC).

    Returns:
        ``YYYY.MM.(N+1)`` within the same month, else ``YYYY.MM.0``.
    """
    month = f"{today.year}.{today.month:02d}"
    head, _, micro = version.rpartition(".")
    if head == month and micro.isdigit():
        return f"{month}.{int(micro) + 1}"
    return f"{month}.0"


def bump(root: Path, today: date) -> str:
    """Write the next version into pyproject.toml and the web package files.

    Args:
        root: The repository root.
        today: The release date (UTC).

    Returns:
        The new version.

    Raises:
        ValueError: If pyproject.toml has no version line.
    """
    pyproject = root / "pyproject.toml"
    text = pyproject.read_text()
    match = _PYPROJECT_VERSION.search(text)
    if match is None:
        raise ValueError("pyproject.toml has no version line")
    new = bumped(match.group(2), today)
    pyproject.write_text(_PYPROJECT_VERSION.sub(rf"\g<1>{new}\g<3>", text, count=1))
    for name in ("package.json", "package-lock.json"):
        path = root / "web" / name
        if not path.exists():
            continue
        doc = json.loads(path.read_text())
        doc["version"] = new
        if "" in doc.get("packages", {}):
            doc["packages"][""]["version"] = new
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return new


def main(argv: list[str] | None = None) -> int:
    """Dispatch a command.

    Args:
        argv: Arguments (defaults to sys.argv[1:]).

    Returns:
        The process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    dec = sub.add_parser("decide")
    dec.add_argument("sha")
    dec.add_argument("--labels", default="")
    dec.add_argument("--github-output", type=Path)
    sub.add_parser("bump")
    args = parser.parse_args(argv)
    if args.command == "bump":
        print(bump(Path.cwd(), datetime.now(UTC).date()))
        return 0
    labels = {label.strip() for label in args.labels.split(",") if label.strip()}
    lines = [f"{k}={v}" for k, v in decide(args.sha, labels).items()]
    print("\n".join(lines))
    if args.github_output is not None:
        with args.github_output.open("a") as out:
            out.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
