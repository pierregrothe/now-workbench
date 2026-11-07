# tests/test_cli_id_guard.py
# Every CLI argument naming a bundle, template or capture file refuses ids that escape (STORY-056).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests for the CLI identifier guard: the API's `safe_child` rule, applied before a command."""

import ast
from pathlib import Path

import click
import pytest
import typer
import typer.main
from typer.testing import CliRunner

from now_workbench.interfaces.cli.ids import safe_id
from now_workbench.interfaces.cli.main import app
from now_workbench.platform.config.paths import UnsafePathError, check_name

CLI = Path(__file__).resolve().parents[1] / "src" / "now_workbench" / "interfaces" / "cli"
ID_PARAMS = {
    "bundle_id",
    "bundle_a",
    "bundle_b",
    "source_id",
    "target_id",
    "template_id",
    "target_bundle_id",
    "filename",
}
BAD_IDS = ["../x", "a/b", "/etc/passwd", "", ".hidden", "a..b", "x" * 129]
FILLER = {"step_number": "1", "customer_name": "Acme"}


def _guarded(param: click.Parameter) -> bool:
    return getattr(param.callback, "__name__", "") == "safe_id"


def _commands() -> list[tuple[list[str], click.Command]]:
    found: list[tuple[list[str], click.Command]] = []

    def walk(cmd: click.Command, path: list[str]) -> None:
        subcommands = getattr(cmd, "commands", None)
        if subcommands is not None:
            for name, sub in subcommands.items():
                walk(sub, [*path, name])
        elif any(_guarded(p) for p in cmd.params):
            found.append((path, cmd))

    walk(typer.main.get_command(app), [])
    return found


def _invocations() -> list[tuple[str, list[str]]]:
    """One argv per guarded argument of every command, that argument set to a placeholder."""
    cases = []
    for path, cmd in _commands():
        args = [p for p in cmd.params if p.param_type_name == "argument"]
        opts = [p for p in cmd.params if p.param_type_name == "option" and p.required]
        for target in (p for p in args if _guarded(p)):
            argv = list(path)
            for p in args:
                argv.append("{bad}" if p is target else FILLER.get(str(p.name), "good-id"))
            for o in opts:
                argv += [o.opts[0], "x"]
            cases.append((f"{' '.join(path)}:{target.name}", argv))
    return cases


def _is_command(fn: ast.FunctionDef) -> bool:
    return any("command" in ast.unparse(d) for d in fn.decorator_list)


def test_cli_guards_every_id_argument_in_the_source() -> None:
    """Structural check: every ID-named parameter of a command carries `safe_id`."""
    unguarded = []
    for path in CLI.glob("*.py"):
        for fn in ast.walk(ast.parse(path.read_text())):
            if not isinstance(fn, ast.FunctionDef) or not _is_command(fn):
                continue
            params = fn.args.args
            defaults = [None] * (len(params) - len(fn.args.defaults)) + list(fn.args.defaults)
            for arg, default in zip(params, defaults, strict=True):
                guarded = default is not None and "callback=safe_id" in ast.unparse(default)
                if arg.arg in ID_PARAMS and not guarded:
                    unguarded.append(f"{path.name}:{fn.name}:{arg.arg}")
    assert unguarded == []


def test_cli_finds_the_guarded_commands() -> None:
    names = {" ".join(path) for path, _ in _commands()}
    assert {"demo inspect", "demo clone", "demo fluent diff", "template generate"} <= names
    assert len(names) == 24


@pytest.mark.parametrize(("case", "argv"), _invocations(), ids=[c for c, _ in _invocations()])
@pytest.mark.parametrize(
    "bad", BAD_IDS, ids=["dotdot-slash", "slash", "abs", "empty", "hidden", "dots", "long"]
)
def test_cli_refuses_an_unsafe_id_before_running(
    case: str, argv: list[str], bad: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundles = tmp_path / "bundles"
    bundles.mkdir()
    monkeypatch.setenv("WORKBENCH_BUNDLES_DIR", str(bundles))
    before = sorted(tmp_path.rglob("*"))
    res = CliRunner().invoke(app, [bad if a == "{bad}" else a for a in argv])
    assert res.exit_code == 2, (case, res.output)
    assert "Invalid name" in res.output
    assert sorted(tmp_path.rglob("*")) == before


def test_safe_id_passes_valid_ids_and_omitted_arguments() -> None:
    assert safe_id("sample-ai-assistant") == "sample-ai-assistant"
    assert safe_id("proof_01.webm") == "proof_01.webm"
    assert safe_id(None) is None
    with pytest.raises(typer.BadParameter) as err:
        safe_id("../x")
    assert str(err.value) == (
        "Invalid name '../x': use letters, digits, '.', '_' or '-' (max 128 characters)."
    )


def test_check_name_is_the_rule_safe_child_applies() -> None:
    assert check_name("a" * 128) == "a" * 128
    for bad in BAD_IDS:
        with pytest.raises(UnsafePathError):
            check_name(bad)
