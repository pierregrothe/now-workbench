# scripts/dev-tools/find_capability.py
# "Does this already exist?" -- rank src/now_workbench's public symbols against a need in words.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Search the code for a capability before writing one (ADR-033).

Describe the need in plain words, not the name you were about to give it::

    python scripts/dev-tools/find_capability.py resolve an instance owned by the current user
    python scripts/dev-tools/find_capability.py --semantic count tokens billed this month

The field is every public (no leading underscore) module-level function and class in
``src/now_workbench``, with the first line of its docstring; a name in a domain's ``__all__`` is
tagged ``export`` (import it from ``now_workbench.domains.<name>``), anything else ``public``.

LEXICAL (always): words of the query against the words of each name and summary, weighted by
how rare a word is in the field (a name match counts double). Fast, free, and blind to paraphrase.

SEMANTIC (``--semantic``): one TypeSafe Jev request asks, for each candidate, the probability
that it already provides the need; results are ranked, never thresholded (alphaseeker measured
true hits from 0.32 to 0.87 with a wrong one at 0.48). It needs ``TYPESAFE_API_KEY`` and costs a
fraction of a cent per query. With no key, or when any request fails, it prints
``[SEMANTIC] not run -- <reason>`` and makes no claim; it never fills in a partial answer.
"""

import argparse
import ast
import math
import os
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import httpx

__all__ = [
    "Capability",
    "index",
    "lexical_search",
    "main",
    "semantic_search",
    "words",
]

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "now_workbench"
ENDPOINT = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-1.13.0"  # pinned: "jev-latest" moves; override with TYPESAFE_MODEL
CHUNK = 700  # candidates per request
MIN_SUMMARY = 15  # a candidate needs a summary this long for Jev to judge it
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_RULES = (
    "Score HIGH only for a genuine substitute -- something the developer should call instead of "
    "writing new code. Score LOW for: a capability that merely handles the same data type or "
    "lives in the same domain; one that is a single step of the described job but not the job; "
    "one that does the inverse or a neighbouring operation."
)
_STOP = frozenset(
    "a an and are as at be by for from get in into is it of on or set the this to with".split()
)


@dataclass(frozen=True, slots=True)
class Capability:
    """One public symbol: what it is called, where it lives and what its docstring says."""

    name: str
    tier: str  # "export" (in a domain's __all__) or "public"
    location: str  # "src/now_workbench/...py:line"
    summary: str


def words(text: str) -> list[str]:
    """Split text into lower-case words: snake_case and camelCase are broken, plurals folded.

    Args:
        text: A name, a summary or a query.

    Returns:
        The words, stop words removed.
    """
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    out = []
    for word in re.findall(r"[a-z0-9]+", spaced.lower()):
        if word in _STOP:
            continue
        if len(word) > 4 and word.endswith("ies"):
            word = word[:-3] + "y"
        elif len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        out.append(word)
    return out


def _exports(src: Path) -> set[str]:
    names: set[str] = set()
    for init in (src / "domains").glob("*/__init__.py"):
        for node in ast.walk(ast.parse(init.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets
            ):
                names |= {e.value for e in ast.walk(node.value) if isinstance(e, ast.Constant)}
    return names


def index(src: Path = SRC) -> list[Capability]:
    """Collect every public module-level function and class (parsed, never imported).

    Args:
        src: The package directory.

    Returns:
        The capabilities, in path order.
    """
    exported = _exports(src)
    found = []
    for path in sorted(src.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(src.parents[1]).as_posix()
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                continue
            if node.name.startswith("_"):
                continue
            doc = (ast.get_docstring(node) or "").strip().splitlines()
            tier = "export" if node.name in exported else "public"
            found.append(Capability(node.name, tier, f"{rel}:{node.lineno}", doc[0] if doc else ""))
    return found


def lexical_search(
    query: str, field: list[Capability], limit: int = 10
) -> list[tuple[float, Capability]]:
    """Rank the field by shared words, rare words counting more and name words double.

    Args:
        query: The need, in words.
        field: The capabilities to rank.
        limit: Maximum results.

    Returns:
        ``(score, capability)`` pairs, best first; only those sharing at least one word.
    """
    wanted = set(words(query))
    docs = [(set(words(c.name)), set(words(c.summary))) for c in field]
    frequency = Counter(w for name, summary in docs for w in name | summary)
    total = len(field) or 1

    def weight(word: str) -> float:
        return math.log(1 + total / (1 + frequency[word]))

    scored = []
    for capability, (name, summary) in zip(field, docs, strict=True):
        score = sum(2 * weight(w) for w in wanted & name) + sum(
            weight(w) for w in wanted & (summary - name)
        )
        if score > 0:
            scored.append((score, capability))
    scored.sort(key=lambda pair: (-pair[0], pair[1].location))
    return scored[:limit]


def _ask(
    client: httpx.Client, key: str, state: str, questions: dict[str, object]
) -> dict[str, float] | None:
    body = {
        "model": os.environ.get("TYPESAFE_MODEL") or DEFAULT_MODEL,
        "state": state,
        "questions": questions,
    }
    for attempt in range(4):
        try:
            response = client.post(ENDPOINT, json=body, headers={"Authorization": f"Bearer {key}"})
        except httpx.TransportError:
            time.sleep(1.5 * (attempt + 1))
            continue
        if response.status_code == 200:
            answers = {k: float(v["noul"]) for k, v in response.json()["answers"].items()}
            return answers if set(answers) == set(questions) else None  # a short reply is no answer
        if response.status_code not in _RETRY_STATUS:
            return None
        time.sleep(1.5 * (attempt + 1))
    return None


def semantic_search(
    query: str,
    field: list[Capability],
    *,
    api_key: str | None,
    client: httpx.Client | None = None,
    limit: int = 10,
) -> tuple[list[tuple[float, Capability]], str | None]:
    """Rank the field by Jev's judgment of whether each candidate already meets the need.

    Args:
        query: The need, in words.
        field: The capabilities to judge.
        api_key: The TypeSafe key (None means the pass cannot run).
        client: An HTTP client (tests pass one with a fake transport).
        limit: Maximum results.

    Returns:
        ``(probability, capability)`` pairs best first, and the reason when the pass did not
        run -- in which case the list is empty, never partial.
    """
    if not api_key:
        return [], "TYPESAFE_API_KEY is not set"
    candidates = [c for c in field if len(c.summary) >= MIN_SUMMARY]
    if not candidates:
        return [], "no capability carries a summary to judge"
    state = f"CAPABILITY THE DEVELOPER IS ABOUT TO BUILD:\n{query}\n\nHOW TO SCORE:\n{_RULES}"
    http = client or httpx.Client(timeout=45.0)
    scored: list[tuple[float, Capability]] = []
    try:
        for start in range(0, len(candidates), CHUNK):
            part = candidates[start : start + CHUNK]
            questions: dict[str, object] = {
                f"c{i}": {
                    "type": "noul",
                    "instructions": f"Existing `{c.name}` ({c.tier}): {c.summary} "
                    "-- does it already provide what the state describes?",
                }
                for i, c in enumerate(part)
            }
            answers = _ask(http, api_key, state, questions)
            if answers is None:
                return [], "a request did not resolve (offline, rejected key, or a short reply)"
            scored += [(answers[f"c{i}"], c) for i, c in enumerate(part)]
    finally:
        if client is None:
            http.close()
    scored.sort(key=lambda pair: (-pair[0], pair[1].location))
    return scored[:limit], None


def _show(title: str, results: list[tuple[float, Capability]]) -> None:
    print(f"[{title}]")
    if not results:
        print("  (nothing)")
    for score, c in results:
        print(f"  {score:6.2f}  {c.name}  [{c.tier}]  {c.location}")
        if c.summary:
            print(f"          {c.summary}")


def main(argv: list[str] | None = None) -> int:
    """Print the lexical results, and the semantic ones when asked.

    Args:
        argv: Arguments (defaults to sys.argv[1:]).

    Returns:
        Always 0: this is a research aid, not a gate.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("query", nargs="+", help="what you are about to build, in plain words")
    parser.add_argument(
        "--semantic", action="store_true", help="also ask TypeSafe Jev (costs a little)"
    )
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)
    query = " ".join(args.query)
    field = index()
    _show("LEXICAL", lexical_search(query, field, args.limit))
    if args.semantic:
        results, reason = semantic_search(
            query, field, api_key=os.environ.get("TYPESAFE_API_KEY"), limit=args.limit
        )
        if reason is not None:
            print(f"[SEMANTIC] not run -- {reason}")
        else:
            _show("SEMANTIC", results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
