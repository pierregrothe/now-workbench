# scripts/hooks/check_domain_card_freshness.py
# Pre-push nudge: name the domain cards whose domain moved on since the card was last committed.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Advisory pre-push nudge for stale domain cards (ADR-033); it never blocks.

For each tracked ``src/**/CLAUDE.md`` it counts the commits that touched the card's directory's
``*.py`` files since the card's own last commit, and the card's age. A card at or past
``MAX_COMMITS`` commits or ``MAX_DAYS`` days is named, with the command to see what changed.
The count is mechanical; whether the card is wrong is a judgment, so the hook only asks.
"""

import subprocess
import sys
import time
from pathlib import Path

__all__ = ["MAX_COMMITS", "MAX_DAYS", "main", "stale_cards"]

MAX_COMMITS = 15
MAX_DAYS = 90


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    return done.stdout.strip()


def stale_cards(now: float | None = None) -> list[str]:
    """Describe each tracked card that has fallen behind its domain.

    Args:
        now: The current time as a Unix timestamp (defaults to the clock).

    Returns:
        One line per stale card.
    """
    current = time.time() if now is None else now
    lines = []
    for card in _git("ls-files", "--", ":(glob)src/**/CLAUDE.md").splitlines():
        sha, _, stamp = _git("log", "-1", "--format=%H %ct", "--", card).partition(" ")
        if not stamp:
            continue  # staged but never committed: nothing to compare against yet
        domain = Path(card).parent.as_posix()
        commits = int(_git("rev-list", "--count", f"{sha}..HEAD", "--", f":(glob){domain}/**/*.py"))
        days = int((current - int(stamp)) // 86400)
        if commits >= MAX_COMMITS or days >= MAX_DAYS:
            lines.append(
                f"{card}: {commits} commits to {domain} and {days} days since the card changed "
                f"(see: git log --oneline {sha[:12]}..HEAD -- {domain})"
            )
    return lines


def main() -> int:
    """Print the stale cards, if any.

    Returns:
        Always 0 (advisory).
    """
    try:
        lines = stale_cards()
    except (subprocess.CalledProcessError, ValueError, OSError) as error:
        print(f"domain-card-freshness: could not check the cards ({error}); skipped.")
        return 0
    if lines:
        print("Domain cards that may need a refresh (advisory, ADR-033):")
        print("\n".join(f"  {line}" for line in lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
