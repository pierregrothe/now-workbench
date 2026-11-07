#!/usr/bin/env python3
# .ratchet/count_card_dead_references.py
# Count identifiers a domain card (src/**/CLAUDE.md) names that src/now_workbench does not define.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Ratchet gate for dead identifiers in the domain cards (ADR-033).

A card is the hand-written account of how to wire into a domain, and an agent that trusts it
acts on the names it gives. When a rename leaves a card pointing at nothing, nothing else fails.

A REFERENCE is an inline backticked span (fenced blocks are skipped) that is a bare or dotted
identifier, with a trailing ``()`` ignored, and that is code-shaped: it has an underscore, a
lower-to-upper camel-case join, or starts with a capital and is at least four characters
long. A name ending in a file extension is a file, not an identifier. A name repeated in one
card counts once, at its first line.

A name is DEFINED when ``ast`` finds it anywhere in ``src/now_workbench/**/*.py`` (never by
importing): a class, function or parameter name, a name any assignment, loop, ``with`` or
import binds, a ``self.x``/``cls.x`` attribute, a string literal that is exactly one identifier
(an ``__all__`` entry, an error code, an environment variable), or a module or package name.
A dotted name resolves part by part. Names whose first part is a builtin, a standard-library
module or an installed third-party package are not checked; a keyword passed to another
function defines nothing. Run it with the project venv's interpreter so "installed" means the
locked dependencies (``ratchet_check.py`` does).

``.ratchet/card_reference_allowlist.txt`` holds ``NAME  # reason`` lines for real names that
are not code in src. An entry without a reason is itself an error and suppresses nothing.

Output: one ``[ERROR] <card>:<line>: <name>`` line per dead reference, then ``Violations: N``.
"""

import ast
import builtins
import importlib.metadata
import itertools
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["Index", "build_index", "dead_references", "defined_names", "main", "references"]

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src" / "now_workbench"
ALLOWLIST = Path(__file__).resolve().parent / "card_reference_allowlist.txt"

_SPAN = re.compile(r"`([^`\n]+)`")
# A leading (dotted) identifier, optionally a decorator, then nothing, a call or a subscript.
_LEAD = re.compile(r"@?([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)(?=$|[(\[])")
_FILE_SUFFIXES = {"py", "md", "ts", "js", "mjs", "json", "yaml", "yml", "toml", "sh", "txt", "css"}
_DDL = re.compile(r"CREATE\s+(?:TABLE|INDEX|UNIQUE\s+INDEX)\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", re.I)


def _code_shaped(name: str) -> bool:
    return (
        "_" in name
        or re.search(r"[a-z][A-Z]", name) is not None
        or (name[0].isupper() and len(name) >= 4)
    )


def references(card: str) -> list[tuple[int, str]]:
    """List the code-shaped identifiers a card names, each once, with its first line.

    A span such as ``Name(conn)``, ``Name[T]`` or ``@decorator`` names its leading identifier.

    Args:
        card: The card's markdown text.

    Returns:
        ``(line, name)`` pairs in order of first appearance.
    """
    seen: dict[str, int] = {}
    fenced = False
    for number, line in enumerate(card.splitlines(), start=1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if fenced:
            continue
        for span in _SPAN.findall(line.replace("``", "`")):
            match = _LEAD.match(span.strip())
            if match is None:
                continue
            name = match.group(1)
            if name.rsplit(".", 1)[-1] in _FILE_SUFFIXES:
                continue
            if "." in name or _code_shaped(name):
                seen.setdefault(name, number)
    return [(line, name) for name, line in seen.items()]


def _bound_names(node: ast.AST) -> set[str]:
    match node:
        case ast.ClassDef(name=name) | ast.FunctionDef(name=name) | ast.AsyncFunctionDef(name=name):
            return {name}
        case ast.arg(arg=name) | ast.TypeVar(name=name) | ast.ParamSpec(name=name):
            return {name}
        case ast.Name(id=name, ctx=ast.Store()):
            return {name}
        case ast.Attribute(value=ast.Name(id="self" | "cls"), attr=attr, ctx=ast.Store()):
            return {attr}
        case ast.alias(name=name, asname=asname):
            return {asname or name.split(".")[0], *name.split(".")}
        case ast.ImportFrom(module=str(module)):
            return set(module.split("."))
        case ast.Constant(value=str(text)):
            return {text} if text.isidentifier() else set(_DDL.findall(text))
    return set()


def _top_level(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        for child in ast.walk(node) if isinstance(node, ast.If) else [node]:
            match child:
                case ast.ClassDef() | ast.FunctionDef() | ast.AsyncFunctionDef():
                    names.add(child.name)
                case ast.Import() | ast.ImportFrom():
                    names |= {a.asname or a.name.split(".")[0] for a in child.names}
                case ast.Assign() | ast.AnnAssign() | ast.AugAssign():
                    names |= {n.id for n in ast.walk(child) if isinstance(n, ast.Name)}
    return names


def _class_members(cls: ast.ClassDef) -> set[str]:
    members: set[str] = set()
    for node in cls.body:
        match node:
            case ast.ClassDef() | ast.FunctionDef() | ast.AsyncFunctionDef():
                members.add(node.name)
            case ast.Assign(targets=targets):
                members |= {t.id for t in targets if isinstance(t, ast.Name)}
            case ast.AnnAssign(target=ast.Name(id=name)):
                members.add(name)
    for node in ast.walk(cls):
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            if isinstance(node.value, ast.Name) and node.value.id in {"self", "cls"}:
                members.add(node.attr)
    return members


def _env_names(cls: ast.ClassDef) -> set[str]:
    """``WORKBENCH_X`` for each field of a settings class declaring ``env_prefix``."""
    prefixes = [
        k.value.value
        for k in ast.walk(cls)
        if isinstance(k, ast.keyword)
        and k.arg == "env_prefix"
        and isinstance(k.value, ast.Constant)
    ]
    fields = [
        n.target.id
        for n in cls.body
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
    ]
    return {
        f"{prefix}{field.upper()}"
        for prefix in prefixes
        if isinstance(prefix, str)
        for field in fields
    }


@dataclass
class Index:
    """What the source tree defines: every name, and the members of each module and class."""

    names: set[str] = field(default_factory=set)
    members: dict[str, set[str]] = field(default_factory=dict)
    modules: set[str] = field(default_factory=set)
    open_classes: set[str] = field(default_factory=set)

    def resolves(self, name: str) -> bool:
        """Say whether a (dotted) name is defined, each part a member of the part before it.

        Args:
            name: The reference.

        Returns:
            True when it resolves.
        """
        parts = name.split(".")
        if parts[0] not in self.names:
            return False
        for parent, part in itertools.pairwise(parts):
            if parent in self.open_classes:
                continue
            known = self.members.get(parent)
            if not (part in known if known is not None else part in self.names):
                return False
        return True


def build_index(src: Path = SRC) -> Index:
    """Parse the source tree (never import it) into an :class:`Index`.

    Args:
        src: The package directory.

    Returns:
        The index.
    """
    index = Index(names={src.name}, modules={src.name})
    bases: dict[str, set[str]] = {}
    for path in src.rglob("*.py"):
        rel = path.relative_to(src).with_suffix("").parts
        index.modules.update(part for part in rel if part != "__init__")
        index.names.update(rel)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        owner = rel[-2] if rel[-1] == "__init__" and len(rel) > 1 else rel[-1]
        if rel == ("__init__",):
            owner = src.name
        index.members.setdefault(owner, set()).update(_top_level(tree))
        parent = (
            rel[-3]
            if rel[-1] == "__init__" and len(rel) > 2
            else (rel[-2] if len(rel) > 1 else src.name)
        )
        index.members.setdefault(parent, set()).add(owner)
        for node in ast.walk(tree):
            index.names |= _bound_names(node)
            if isinstance(node, ast.ClassDef):
                index.members.setdefault(node.name, set()).update(_class_members(node))
                index.names |= _env_names(node)
                bases.setdefault(node.name, set()).update(
                    ast.unparse(b).split("[")[0] for b in node.bases
                )
    for cls, parents in bases.items():
        if any(p.split(".")[-1] not in bases for p in parents if p not in {"object", "Protocol"}):
            index.open_classes.add(cls)
    for _ in range(len(bases)):  # inherited members, to a fixed point
        for cls, parents in bases.items():
            for p in parents:
                index.members[cls] |= index.members.get(p.split(".")[-1], set())
    return index


def defined_names(src: Path = SRC) -> set[str]:
    """Collect every name the source tree defines (parsed, never imported).

    Args:
        src: The package directory.

    Returns:
        The defined names, module and package names included.
    """
    return build_index(src).names


def _external_roots() -> set[str]:
    installed = set(importlib.metadata.packages_distributions())
    installed.discard("now_workbench")
    return set(dir(builtins)) | set(sys.stdlib_module_names) | installed


def _allowlist(path: Path) -> tuple[set[str], list[str]]:
    allowed: set[str] = set()
    errors: list[str] = []
    if not path.exists():
        return allowed, errors
    for number, raw in enumerate(path.read_text().splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, _, reason = line.partition("#")
        if not reason.strip():
            errors.append(f"{path.name}:{number}: '{name.strip()}' has no '# reason'")
            continue
        allowed.add(name.strip())
    return allowed, errors


def dead_references(src: Path = SRC, allowlist: Path = ALLOWLIST) -> list[str]:
    """Report each dead reference in every card under the source tree.

    Args:
        src: The package directory holding the cards.
        allowlist: The allowlist file.

    Returns:
        One error line per dead reference or unexplained allowlist entry.
    """
    index = build_index(src)
    # A project module that shares a stdlib name (`platform`, `profile`) is still checked.
    external = _external_roots() - index.modules
    allowed, errors = _allowlist(allowlist)
    for card in sorted(src.rglob("CLAUDE.md")):
        rel = card.relative_to(src.parents[1]).as_posix()
        for number, name in references(card.read_text(encoding="utf-8")):
            parts = name.split(".")
            if name in allowed or parts[0] in external:
                continue
            if not index.resolves(name):
                errors.append(f"{rel}:{number}: {name}")
    return errors


def main() -> int:
    """Print each dead reference and the violation count.

    Returns:
        Always 0; the ratchet gates on the count.
    """
    errors = dead_references()
    for error in errors:
        print(f"[ERROR] {error}", file=sys.stderr)
    print(f"Violations: {len(errors)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
