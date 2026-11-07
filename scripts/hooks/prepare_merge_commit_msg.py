# scripts/hooks/prepare_merge_commit_msg.py
# prepare-commit-msg hook: rewrite git's default merge subject to Conventional Commits form.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Rewrite ``Merge branch '...'`` subjects to ``chore(merge): Merge branch '...'`` (ADR-032).

The commit-msg gate (``conventional-pre-commit --strict``) has no merge allowance, so a local
merge of ``main`` into a story branch would always abort at it. Only a merge commit whose
subject starts with ``Merge `` is rewritten; anything else is left alone. Always exits 0: the
commit-msg gate stays the enforcement point.
"""

import os
import sys
from pathlib import Path

__all__ = ["is_merge", "main", "rewrite_merge_subject"]


def rewrite_merge_subject(message: str) -> str | None:
    """Return the message with a conventional merge subject, or None when none applies.

    Args:
        message: The full commit message.

    Returns:
        The rewritten message, or None.
    """
    subject, sep, rest = message.partition("\n")
    if not subject.startswith("Merge "):
        return None
    return f"chore(merge): {subject}{sep}{rest}"


def is_merge(source: str | None, git_dir: Path) -> bool:
    """Say whether the commit being prepared is a merge.

    Args:
        source: The commit source git passes (``merge`` for a merge), or None.
        git_dir: The repository's git directory.

    Returns:
        True for a merge commit.
    """
    return source == "merge" or (git_dir / "MERGE_HEAD").exists()


def main(argv: list[str]) -> int:
    """Rewrite the message file in place when it holds a default merge subject.

    Args:
        argv: The message file, then git's commit source (pre-commit forwards both).

    Returns:
        Always 0.
    """
    if not argv:
        return 0
    path = Path(argv[0])
    source = os.environ.get("PRE_COMMIT_COMMIT_MSG_SOURCE") or (argv[1] if len(argv) > 1 else None)
    if not path.exists() or not is_merge(source, path.parent):
        return 0
    rewritten = rewrite_merge_subject(path.read_text(encoding="utf-8"))
    if rewritten is not None:
        path.write_text(rewritten, encoding="utf-8")
        print(f"prepare-commit-msg: {rewritten.partition(chr(10))[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
