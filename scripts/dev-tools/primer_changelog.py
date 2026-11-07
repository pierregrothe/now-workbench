# scripts/dev-tools/primer_changelog.py
# One-line-per-change changelog: validate, add, roll into a release, condense history, status.
# Author: Pierre Grothe
# Date: 2026-10-20
"""Keep a short, tagged changelog, owned by the Primer skill.

This file is the primer skill's template (``reference/templates/primer-changelog.py``);
a project carries an installed copy as ``scripts/dev-tools/primer_changelog.py`` so CI
can run it. Edit the template, then re-install (``/primer changelog install``): the
copy and the template must stay byte-identical.

The contract (why it looks like Claude Code's release notes, not an incident log):

* ONE line per user-visible change, under ``### Added``, ``### Changed``,
  ``### Fixed``, ``### Removed``, ``### Deprecated`` or ``### Security``, at most
  ``maxEntryChars`` characters (default 160), ending in the pull request number.
  The story behind a change lives in the pull request, ``.primer/decisions.md`` and
  ``git log`` -- never here.
* Entries accumulate under ``## [Unreleased]`` and are rolled into
  ``## [VERSION] - DATE`` when a release is cut (in the primer workflow, when an epic
  closes). Internal work (docs, tests, CI, chores, primer syncs) needs no entry.
* A period heading ``## [YYYY.MM]`` holds history condensed from pull-request titles.

Commands::

    primer_changelog.py validate [--require-unreleased] [--format json] [--root DIR]
    primer_changelog.py add --section Fixed --message "..." [--scope s] [--pr 12]
    primer_changelog.py roll VERSION [--date YYYY-MM-DD] [--summary "..."] [--allow-empty]
    primer_changelog.py condense [--since DATE] [--write]
    primer_changelog.py status [--format json]

Optional ``.primer/changelog.json``: ``{"maxEntryChars": 160, "ascii": true}``.
Exit code: 0 ok, 1 validation errors or a refused operation.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import UTC
from datetime import date as _date
from datetime import datetime
from pathlib import Path
from typing import Any

__all__ = ["add_entry", "condense", "main", "roll", "validate"]

SECTIONS = ("Added", "Changed", "Deprecated", "Removed", "Fixed", "Security")
DEFAULT_MAX_ENTRY = 160
UNRELEASED = "Unreleased"

_HEADING = re.compile(r"^## \[([^\]]+)\](?: - (.*))?$")
_VERSION = re.compile(r"^\d{4}\.\d{1,2}\.\d+\Z")
_PERIOD = re.compile(r"^\d{4}\.\d{2}\Z")
_SUBSECTION = re.compile(r"^### (.+?)\s*$")
_BULLET = re.compile(r"^- \S")
_NOTE = re.compile(r"^_[^_].*_$")
_CONVENTIONAL = re.compile(r"^(\w+)(?:\(([^)]*)\))?(!)?(?:\s+[^:]{1,20})?\s*:\s*(.*)$")
_PR_NUMBER = re.compile(r"\(#(\d+)\)\s*$")
_STORY_ID = re.compile(r"^[A-Z]{2,}\.\d+(?:-\d+)?:\s*")
_MERGE_BRANCH = re.compile(r"^Merge pull request #\d+ from [^/\s]+/(?:([\w-]+)/)?")

#: Conventional-commit type -> changelog section; any type absent here is internal.
_TYPE_SECTION = {
    "feat": "Added",
    "fix": "Fixed",
    "refactor": "Changed",
    "perf": "Changed",
    "build": "Changed",
    "revert": "Changed",
    "audit": "Changed",
    "merge": "Changed",
}
#: A scope that marks the change as internal, whatever its type.
_INTERNAL_SCOPES = frozenset({"test", "tests", "ci", "primer", "docs", "deps", "deps-dev", "version", "merge"})
#: A branch-name prefix that types a merge commit whose title is not conventional.
_BRANCH_SECTION = {
    "feature": "Added",
    "feat": "Added",
    "fix": "Fixed",
    "bugfix": "Fixed",
    "hotfix": "Fixed",
    "refactor": "Changed",
    "perf": "Changed",
}
_GIT_TIMEOUT = 120
_PATCH = 2  # index of the micro number in a split version


@dataclass(frozen=True)
class Config:
    """Per-project settings read from ``.primer/changelog.json``."""

    max_entry: int = DEFAULT_MAX_ENTRY
    ascii_only: bool = True


@dataclass
class Block:
    """One ``## [name]`` block: its heading line and the lines under it."""

    name: str
    heading: str
    lines: list[str]


def load_config(root: Path) -> Config:
    """Read ``.primer/changelog.json``; defaults when absent or unreadable.

    Args:
        root: The project root.

    Returns:
        The settings in force.
    """
    try:
        raw = json.loads((root / ".primer" / "changelog.json").read_text(encoding="utf-8"))
    except OSError, ValueError:
        return Config()
    if not isinstance(raw, dict):
        return Config()
    limit = raw.get("maxEntryChars", DEFAULT_MAX_ENTRY)
    return Config(
        max_entry=limit if isinstance(limit, int) and limit > 0 else DEFAULT_MAX_ENTRY,
        ascii_only=raw.get("ascii", True) is not False,
    )


def split_blocks(text: str) -> tuple[list[str], list[Block]]:
    """Split a changelog into its preamble and its ``## [name]`` blocks.

    Args:
        text: The file's text.

    Returns:
        The lines before the first block, then the blocks in file order.
    """
    preamble: list[str] = []
    blocks: list[Block] = []
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            blocks.append(Block(match.group(1), line, []))
        elif blocks:
            blocks[-1].lines.append(line)
        else:
            preamble.append(line)
    return preamble, blocks


def join_blocks(preamble: list[str], blocks: list[Block]) -> str:
    """Render a preamble and blocks back to text, one blank line between blocks.

    Args:
        preamble: Lines before the first block.
        blocks: The blocks, in order.

    Returns:
        The file text, ending in one newline.
    """
    out = list(preamble)
    while out and not out[-1].strip():
        out.pop()
    for block in blocks:
        body = list(block.lines)
        while body and not body[-1].strip():
            body.pop()
        while body and not body[0].strip():
            body.pop(0)
        out += ["", block.heading, ""] if body else ["", block.heading]
        out += body
    return "\n".join(out).strip("\n") + "\n"


def _heading_errors(blocks: list[Block]) -> list[str]:
    errors: list[str] = []
    names = [b.name for b in blocks]
    if UNRELEASED not in names:
        errors.append("no ## [Unreleased] block")
    elif names[0] != UNRELEASED:
        errors.append("## [Unreleased] must be the first block")
    for name, count in Counter(names).items():
        if count > 1:
            errors.append(f"duplicate block [{name}]")
    for name in names:
        if name != UNRELEASED and not (_VERSION.match(name) or _PERIOD.match(name)):
            errors.append(f"block [{name}] is neither [Unreleased], [YYYY.MM.N] nor [YYYY.MM]")
    return errors


def _line_error(line: str, cfg: Config) -> str | None:
    """Return what is wrong with one body line, or None when it is allowed."""
    if not line.strip() or _NOTE.match(line):
        return None
    sub = _SUBSECTION.match(line)
    if sub:
        return None if sub.group(1) in SECTIONS else f"unknown section '### {sub.group(1)}' (use {', '.join(SECTIONS)})"
    if not _BULLET.match(line):
        return "only '### Section' headings and one-line '- ' bullets are allowed (no prose, no nested or continued bullets)"
    if len(line) - 2 > cfg.max_entry:
        return f"entry is {len(line) - 2} characters; the cap is {cfg.max_entry} -- say what changed in one line, the story belongs in the PR"
    if cfg.ascii_only and not line.isascii():
        return "non-ASCII character"
    return None


def _duplicate_sections(block: Block) -> list[str]:
    names = [m.group(1) for line in block.lines if (m := _SUBSECTION.match(line))]
    return [
        f"[{block.name}] has '### {n}' twice (a union merge of two branches?): merge them"
        for n, c in Counter(names).items()
        if c > 1
    ]


def _merge_duplicate_sections(lines: list[str]) -> list[str]:
    """Fold repeated ``### Section`` headings into one, in canonical order."""
    names = [m.group(1) for line in lines if (m := _SUBSECTION.match(line))]
    if len(names) == len(set(names)):
        return lines
    head: list[str] = []
    groups: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        m = _SUBSECTION.match(line)
        if m:
            current = m.group(1)
            groups.setdefault(current, [])
        elif current is None:
            head.append(line)
        elif _BULLET.match(line):
            groups[current].append(line)
    out = [line for line in head if line.strip()]
    for name in sorted(groups, key=lambda n: SECTIONS.index(n) if n in SECTIONS else len(SECTIONS)):
        out += ["", f"### {name}", *groups[name]]
    return out


def validate(text: str, cfg: Config, *, require_unreleased: bool = False) -> list[str]:
    """Check a changelog against the contract.

    Args:
        text: The file's text.
        cfg: The project's settings.
        require_unreleased: Also demand at least one entry under ``[Unreleased]``.

    Returns:
        Human-readable errors, empty when the file is clean.
    """
    preamble, blocks = split_blocks(text)
    errors = [] if preamble and preamble[0].startswith("# ") else ["the file must start with a '# Changelog' title"]
    errors += _heading_errors(blocks)
    for block in blocks:
        errors += _duplicate_sections(block)
        for offset, line in enumerate(block.lines, start=1):
            problem = _line_error(line, cfg)
            if problem:
                errors.append(f"[{block.name}] +{offset}: {problem}: {line[:60]!r}")
    if require_unreleased:
        unreleased = next((b for b in blocks if b.name == UNRELEASED), None)
        if unreleased is None or not any(_BULLET.match(line) for line in unreleased.lines):
            errors.append("[Unreleased] has no entry: add one line with `primer_changelog.py add`")
    return errors


def _insert_bullet(lines: list[str], section: str, bullet: str) -> list[str]:
    """Return ``lines`` with ``bullet`` appended to ``### section`` (created in canonical order)."""
    out = list(lines)
    start = next((i for i, line in enumerate(out) if line.strip() == f"### {section}"), None)
    if start is None:
        rank = SECTIONS.index(section)
        later = [
            i
            for i, line in enumerate(out)
            if (m := _SUBSECTION.match(line)) and m.group(1) in SECTIONS and SECTIONS.index(m.group(1)) > rank
        ]
        at = later[0] if later else len(out)
        while at > 0 and not out[at - 1].strip():
            at -= 1
        out[at:at] = ["", f"### {section}", bullet]
        return out
    end = start + 1
    while end < len(out) and not _SUBSECTION.match(out[end]):
        end += 1
    while end > start + 1 and not out[end - 1].strip():
        end -= 1
    out.insert(end, bullet)
    return out


def add_entry(text: str, section: str, message: str, cfg: Config, *, scope: str = "", pr: int | None = None) -> str:
    """Append one entry to ``[Unreleased]``.

    Args:
        text: The file's text.
        section: One of :data:`SECTIONS` (case-insensitive).
        message: The change, in one line.
        cfg: The project's settings.
        scope: Optional prefix, rendered ``scope: message``.
        pr: Optional pull request number, rendered ``(#N)``.

    Returns:
        The new file text.

    Raises:
        ValueError: On an unknown section, a multi-line or over-long message, or no ``[Unreleased]`` block.
    """
    name = next((s for s in SECTIONS if s.lower() == section.strip().lower()), None)
    if name is None:
        raise ValueError(f"unknown section {section!r}; use one of {', '.join(SECTIONS)}")
    body = " ".join(message.split())
    if not body:
        raise ValueError("the message is empty")
    tag = " ".join(scope.split())
    entry = f"{tag}: {body}" if tag else body
    if pr is not None:
        entry += f" (#{pr})"
    problem = _line_error(f"- {entry}", cfg)
    if problem:
        raise ValueError(problem)
    preamble, blocks = split_blocks(text)
    target = next((b for b in blocks if b.name == UNRELEASED), None)
    if target is None:
        raise ValueError("no ## [Unreleased] block to add to")
    target.lines = _merge_duplicate_sections(target.lines)
    if f"- {entry}" not in target.lines:
        target.lines = _insert_bullet(target.lines, name, f"- {entry}")
    return join_blocks(preamble, blocks)


def _without_empty_sections(lines: list[str]) -> list[str]:
    """Drop every ``### Section`` heading that has no bullet under it."""
    out: list[str] = []
    for index, line in enumerate(lines):
        if _SUBSECTION.match(line):
            rest = lines[index + 1 :]
            following = next((i for i, nxt in enumerate(rest) if _SUBSECTION.match(nxt)), len(rest))
            if not any(_BULLET.match(nxt) for nxt in rest[:following]):
                continue
        out.append(line)
    return out


def roll(text: str, version: str, date: str, *, summary: str = "", allow_empty: bool = False) -> str:
    """Turn ``[Unreleased]`` into ``[VERSION] - DATE`` and start a fresh ``[Unreleased]``.

    Args:
        text: The file's text.
        version: The release version, ``YYYY.MM.N``.
        date: ISO release date.
        summary: Optional one-line description of the release (an epic's title).
        allow_empty: Release with no entries (a hotfix or an epic whose work needs no line); the note says so.

    Returns:
        The new file text.

    Raises:
        ValueError: On a malformed or existing version, a malformed summary, or an empty ``[Unreleased]``.
    """
    if not _VERSION.match(version):
        raise ValueError(f"version {version!r} is not YYYY.MM.N")
    try:
        _date.fromisoformat(date)
    except ValueError as exc:
        raise ValueError(f"date {date!r} is not an ISO date") from exc
    preamble, blocks = split_blocks(text)
    if any(b.name == version for b in blocks):
        raise ValueError(f"[{version}] already exists")
    current = next((b for b in blocks if b.name == UNRELEASED), None)
    if current is None:
        raise ValueError("no ## [Unreleased] block to release")
    if not any(_BULLET.match(line) for line in current.lines):
        if not allow_empty:
            raise ValueError("[Unreleased] has no entries to release")
        summary = summary or "No user-visible changes."
    note = " ".join(summary.split()).strip("_")
    released = Block(
        version,
        f"## [{version}] - {date}",
        ([f"_{note}_", ""] if note else []) + _without_empty_sections(_merge_duplicate_sections(current.lines)),
    )
    fresh = Block(UNRELEASED, f"## [{UNRELEASED}]", [])
    return join_blocks(preamble, [fresh, released, *[b for b in blocks if b is not current]])


def _git(root: Path, *args: str) -> str:
    git = shutil.which("git") or "git"
    done = subprocess.run([git, *args], cwd=root, capture_output=True, text=True, timeout=_GIT_TIMEOUT, check=False)
    if done.returncode != 0:
        raise ValueError(f"git {' '.join(args[:2])} failed: {done.stderr.strip()[:200]}")
    return done.stdout


def _title_of(subject: str, body: str) -> tuple[str, str]:
    """Return ``(title, branch_kind)``; a merge commit's title is the first line of its body."""
    if not subject.startswith("Merge pull request"):
        return subject, ""
    first = next((line.strip() for line in body.splitlines() if line.strip()), "")
    number = re.search(r"#(\d+)", subject)
    branch = _MERGE_BRANCH.match(subject)
    return (f"{first} (#{number.group(1)})" if first and number else ""), (branch.group(1) or "") if branch else ""


def _classify(title: str, branch_kind: str = "") -> tuple[str, str] | None:
    """Map a pull-request title (and a merge branch's prefix) to ``(section, entry)``, or None if internal."""
    match = _CONVENTIONAL.match(title)
    if match:
        kind, scope, _bang, rest = match.groups()
        section = _TYPE_SECTION.get(kind.lower())
        head = (scope or "").replace(",", " ").split()
        if section is None or not _PR_NUMBER.sub("", rest).strip() or (head and head[0].lower() in _INTERNAL_SCOPES):
            return None
        if head and head[0].lower() in {"security", "deps-security"}:
            section = "Security"
        return section, (rest if kind.lower() == "merge" or not scope else f"{scope}: {rest}")
    if _STORY_ID.match(title):
        return "Changed", title
    section = _BRANCH_SECTION.get(branch_kind)
    return (section, title) if section and title else None


def _clip(entry: str, limit: int) -> str:
    """Trim an over-long entry at a word boundary, keeping the trailing ``(#N)``."""
    if len(entry) <= limit:
        return entry
    pr = _PR_NUMBER.search(entry)
    tail = f" (#{pr.group(1)})" if pr else ""
    head = entry[: pr.start()].rstrip() if pr else entry
    room = max(1, limit - len(tail) - 3)
    cut = head[:room].rsplit(" ", 1)[0].rstrip(",;:- ")
    return f"{cut}...{tail}"


#: Typographic characters a pull-request title may carry, and their ASCII spelling.
_ASCII_TABLE = {
    0x2013: "-",
    0x2014: "--",
    0x2018: "'",
    0x2019: "'",
    0x201C: '"',
    0x201D: '"',
    0x2192: "->",
    0x2026: "...",
}


def _ascii(entry: str) -> str:
    """ASCII spelling of an entry: typographic marks by table, accents dropped, the rest ``?``."""
    plain = unicodedata.normalize("NFKD", entry.translate(_ASCII_TABLE))
    return "".join(ch for ch in plain if not unicodedata.combining(ch)).encode("ascii", "replace").decode("ascii")


def _month_of(stamp: str) -> str:
    return datetime.fromtimestamp(int(stamp), UTC).strftime("%Y.%m")


def _collect(raw: str, cfg: Config) -> tuple[dict[str, dict[str, list[str]]], int, int]:
    """Group the first-parent history into ``{month: {section: [bullet]}}``; return it with kept and omitted counts."""
    months: dict[str, dict[str, list[str]]] = {}
    kept = omitted = 0
    for record in raw.split("\x1e"):
        if not record.strip():
            continue
        stamp, subject, body = [*record.strip("\n").split("\x1f"), "", ""][:3]
        classified = _classify(*_title_of(subject.strip(), body))
        if classified is None:
            omitted += 1
            continue
        section, entry = classified
        text = " ".join(entry.split())
        bucket = months.setdefault(_month_of(stamp), {}).setdefault(section, [])
        bullet = f"- {_clip(_ascii(text) if cfg.ascii_only else text, cfg.max_entry)}"
        if bullet not in bucket:
            bucket.append(bullet)
            kept += 1
    return months, kept, omitted


def _sort_key(name: str) -> tuple[int, int, int]:
    """Newest first: a release ``Y.M.N`` sorts before its month's period block ``Y.M``."""
    parts = [int(part) for part in name.split(".")]
    return (parts[0], parts[1], parts[_PATCH] if len(parts) > _PATCH else -1)


def _preamble(existing: list[str], sha: str) -> list[str]:
    """Keep a preamble that already states the contract; otherwise write one."""
    if any("One line per change" in line for line in existing):
        return existing
    title = existing[0] if existing and existing[0].startswith("# ") else "# Changelog"
    return [
        title,
        "",
        "One line per change, newest first: `### Added`, `### Changed`, `### Fixed`, `### Removed`, `### Security`.",
        "The story behind a change is in its pull request (the number in brackets) and in `git log`.",
        "Releases are cut when an epic closes. Months below were condensed from pull-request titles:",
        f"internal chores, docs, tests and CI are omitted, and the long-form entries are in git history at {sha}.",
    ]


def condense(root: Path, cfg: Config, since: str = "") -> tuple[str, dict[str, int]]:
    """Rebuild the history as one short entry per user-visible pull request, grouped by month.

    Reads the first-parent history and keeps ``feat``, ``fix``, ``refactor``, ``perf``,
    ``build`` and ``revert`` work (a merge commit's body title, or its branch prefix, when the
    squash title is not conventional; untyped story titles such as ``CAL.09: ...``). Chores,
    docs, tests, CI, primer syncs and dependency churn are dropped, and each entry is clipped to
    the cap. Months are UTC. ``[Unreleased]`` is kept, and so is every other block that already
    meets the contract (a release rolled since the last condense, an earlier month); blocks in
    the old long form are replaced.

    Args:
        root: The project root (its ``CHANGELOG.md`` supplies the blocks to keep).
        cfg: The project's settings.
        since: Only history on or after this ISO date; empty for all of it.

    Returns:
        The new file text and counts: ``kept``, ``omitted`` and ``months``.

    Raises:
        ValueError: When git fails or no history is found.
    """
    args = ["log", "--first-parent", "--format=%at%x1f%s%x1f%b%x1e"]
    if since:
        args.append(f"--since={since}")
    months, kept, omitted = _collect(_git(root, *args), cfg)
    if not months:
        raise ValueError("no history to condense")
    path = root / "CHANGELOG.md"
    old_pre, old_blocks = split_blocks(path.read_text(encoding="utf-8")) if path.exists() else ([], [])
    unreleased = next((b for b in old_blocks if b.name == UNRELEASED), Block(UNRELEASED, f"## [{UNRELEASED}]", []))
    compliant = [
        b
        for b in old_blocks
        if b.name != UNRELEASED and b.name not in months and not any(_line_error(line, cfg) for line in b.lines)
    ]
    rebuilt = []
    for month, sections in months.items():
        lines = ["_Condensed from pull-request titles._", ""]
        for section in SECTIONS:
            if section in sections:
                lines += [f"### {section}", *sections[section], ""]
        rebuilt.append(Block(month, f"## [{month}]", lines))
    ordered = sorted([*compliant, *rebuilt], key=lambda b: _sort_key(b.name), reverse=True)
    sha = _git(root, "rev-parse", "--short", "HEAD").strip()
    return join_blocks(_preamble(old_pre, sha), [unreleased, *ordered]), {
        "kept": kept,
        "omitted": omitted,
        "months": len(months),
    }


def status(text: str, cfg: Config) -> dict[str, Any]:
    """Summarize a changelog.

    Args:
        text: The file's text.
        cfg: The project's settings.

    Returns:
        Counts, the last release and the longest entry.
    """
    _pre, blocks = split_blocks(text)
    bullets = [line for b in blocks for line in b.lines if _BULLET.match(line)]
    unreleased = next((b for b in blocks if b.name == UNRELEASED), None)
    return {
        "lines": len(text.splitlines()),
        "blocks": len(blocks),
        "unreleased_entries": sum(1 for line in (unreleased.lines if unreleased else []) if _BULLET.match(line)),
        "last_release": next((b.name for b in blocks if _VERSION.match(b.name)), None),
        "longest_entry": max((len(line) - 2 for line in bullets), default=0),
        "max_entry": cfg.max_entry,
        "errors": len(validate(text, cfg)),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Short, tagged changelog: validate, add, roll, condense, status.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="project root (default: current directory)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", type=Path, default=argparse.SUPPRESS)
    common.add_argument("--format", choices=("text", "json"), default=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate", parents=[common], help="check the file against the contract")
    check.add_argument("--require-unreleased", action="store_true", help="demand an entry under [Unreleased]")
    add = sub.add_parser("add", parents=[common], help="append one entry to [Unreleased]")
    add.add_argument("--section", required=True, help=", ".join(SECTIONS))
    add.add_argument("--message", required=True)
    add.add_argument("--scope", default="")
    add.add_argument("--pr", type=int)
    rolled = sub.add_parser("roll", parents=[common], help="release [Unreleased] as VERSION")
    rolled.add_argument("version")
    rolled.add_argument("--date", default=datetime.now(UTC).date().isoformat())
    rolled.add_argument("--summary", default="")
    rolled.add_argument("--allow-empty", action="store_true", help="release even with no entries")
    cond = sub.add_parser("condense", parents=[common], help="rebuild history from pull-request titles")
    cond.add_argument("--since", default="")
    cond.add_argument("--write", action="store_true", help="write CHANGELOG.md (default: report only)")
    sub.add_parser("status", parents=[common], help="counts and the longest entry")
    return parser


def _emit(args: argparse.Namespace, payload: dict[str, Any], lines: list[str]) -> None:
    print(json.dumps(payload) if args.format == "json" else "\n".join(lines))


def _run(args: argparse.Namespace, path: Path, cfg: Config) -> int:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if args.command == "validate":
        errors = validate(text, cfg, require_unreleased=args.require_unreleased)
        _emit(args, {"ok": not errors, "errors": errors}, errors or ["CHANGELOG.md: ok"])
        return 1 if errors else 0
    if args.command == "add":
        path.write_text(
            add_entry(text, args.section, args.message, cfg, scope=args.scope, pr=args.pr), encoding="utf-8"
        )
        _emit(args, {"ok": True}, [f"added to [{UNRELEASED}]"])
        return 0
    if args.command == "roll":
        path.write_text(
            roll(text, args.version, args.date, summary=args.summary, allow_empty=args.allow_empty), encoding="utf-8"
        )
        _emit(args, {"ok": True, "version": args.version}, [f"[{UNRELEASED}] -> [{args.version}]"])
        return 0
    if args.command == "condense":
        rebuilt, counts = condense(args.root, cfg, args.since)
        if args.write:
            path.write_text(rebuilt, encoding="utf-8")
        _emit(
            args,
            {"written": args.write, **counts, "lines": len(rebuilt.splitlines())},
            [f"{counts} -> {len(rebuilt.splitlines())} lines ({'written' if args.write else 'dry run'})"],
        )
        return 0
    report = status(text, cfg)
    _emit(args, report, [f"{k}: {v}" for k, v in report.items()])
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the command line.

    Args:
        argv: Arguments after the program name; ``sys.argv`` when omitted.

    Returns:
        0 on success, 1 on validation errors or a refused operation.
    """
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    args.root = root
    try:
        return _run(args, root / "CHANGELOG.md", load_config(root))
    except ValueError as exc:
        print(f"primer_changelog: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
