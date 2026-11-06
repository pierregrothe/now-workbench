# tests/test_deepfix_fluent_nested_columns.py
# Regression tests: fluent column parsing with nested objects, arrays and braces in strings
# Author: Pierre Grothe
# Date: 2026-11-06

from now_workbench.fluent.engine import FluentEngine
from now_workbench.fluent.models import FluentColumnDef


def _columns(columns_src: str) -> dict[str, FluentColumnDef]:
    src = "Table({ name: 'x_t', label: 'T', schema: {" + columns_src + "} })"
    schemas = FluentEngine().parse_source(src)
    assert len(schemas) == 1
    return {c.name: c for c in schemas[0].columns}


def test_parse_columns_nested_object_keeps_column() -> None:
    cols = _columns(
        "status: ChoiceColumn({ label: 'Status', choices: { a: { label: 'A' } } }),"
        " other: StringColumn({ label: 'Other', mandatory: true }),"
    )
    assert set(cols) == {"status", "other"}
    assert cols["other"].mandatory is True


def test_parse_columns_nested_array_keeps_column() -> None:
    cols = _columns(
        "tags: StringColumn({ label: 'Tags', values: [{ a: 1 }, { b: 2 }], maxLength: 40 }),"
    )
    assert cols["tags"].max_length == 40


def test_parse_columns_braces_in_strings_do_not_unbalance() -> None:
    cols = _columns(
        "a: StringColumn({ label: 'weird } brace', maxLength: 5 }),"
        " b: StringColumn({ label: 'x { y', mandatory: true }),"
    )
    assert set(cols) == {"a", "b"}
    assert cols["a"].max_length == 5


def test_compute_diff_nested_column_unchanged_is_identical() -> None:
    src = "Table({ name: 'x_t', schema: { s: ChoiceColumn({ choices: { a: { label: 'A' } } }) } })"
    engine = FluentEngine()
    diff = engine.compute_diff(engine.parse_source(src), engine.parse_source(src))
    assert diff.identical
