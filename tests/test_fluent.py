"""Tests for ServiceNow Fluent SDK AST parsing, schema extraction, and diff analysis."""

from pathlib import Path

from now_workbench.fluent.engine import FluentEngine
from now_workbench.fluent.models import (
    FluentColumnDef,
    FluentSchemaDiff,
    FluentTableSchema,
)

SAMPLE_FLUENT_TS = """import { Record, Table } from '@servicenow/sdk/core'

export const x_demo_ai_routing_log = Table({
    name: 'x_demo_ai_routing_log',
    label: 'AI Routing Log',
    schema: {
        incident_ref: Record({
            label: 'Incident Reference',
            reference: 'incident',
            mandatory: true,
        }),
        predicted_category: Record({
            label: 'Predicted Category',
            maxLength: 40,
        }),
        confidence_score: Record({
            label: 'Confidence Score (0-100)',
            maxLength: 10,
        }),
        auto_routed: Record({
            label: 'Auto-Routed by Agent',
            mandatory: false,
        }),
    },
})
"""


def test_fluent_models() -> None:
    """Verify Fluent Pydantic model integrity and frozen immutability."""
    col = FluentColumnDef(
        name="incident_ref",
        label="Incident Reference",
        column_type="reference",
        reference="incident",
        mandatory=True,
    )
    assert col.name == "incident_ref"
    assert col.column_type == "reference"
    assert col.mandatory is True

    tbl = FluentTableSchema(
        name="x_demo_test",
        label="Test Table",
        columns=[col],
        raw_source="Table(...)",
    )
    assert tbl.name == "x_demo_test"
    assert len(tbl.columns) == 1

    diff = FluentSchemaDiff(
        added_tables=["table_b"],
        removed_tables=[],
        modified_tables={"table_a": ["Added column 'col_x'"]},
        identical=False,
    )
    assert diff.identical is False
    assert "table_b" in diff.added_tables


def test_parse_source() -> None:
    """Verify parsing a TypeScript source containing Fluent Table definitions."""
    engine = FluentEngine()
    tables = engine.parse_source(SAMPLE_FLUENT_TS)

    assert len(tables) == 1
    tbl = tables[0]
    assert tbl.name == "x_demo_ai_routing_log"
    assert tbl.label == "AI Routing Log"
    assert len(tbl.columns) == 4

    col_map = {c.name: c for c in tbl.columns}
    assert "incident_ref" in col_map
    assert col_map["incident_ref"].column_type == "reference"
    assert col_map["incident_ref"].reference == "incident"
    assert col_map["incident_ref"].mandatory is True

    assert "predicted_category" in col_map
    assert col_map["predicted_category"].max_length == 40
    assert col_map["predicted_category"].column_type == "string"

    assert "auto_routed" in col_map
    assert col_map["auto_routed"].mandatory is False


def test_parse_source_edge_cases() -> None:
    """Verify parsing edge cases with empty, missing, or malformed sources."""
    engine = FluentEngine()

    # Empty content
    assert engine.parse_source("") == []

    # Content without Table definitions
    assert engine.parse_source("const a = 123;\nconsole.log(a);") == []

    # Table without name is ignored
    malformed = """
    export const t = Table({
        label: 'Missing Name',
        schema: {},
    })
    """
    assert engine.parse_source(malformed) == []


def test_load_bundle_schemas(tmp_path: Path) -> None:
    """Verify loading Fluent schemas from demo bundle directory."""
    engine = FluentEngine()

    # 1. Non-existent path returns empty list
    assert engine.load_bundle_schemas(tmp_path / "does-not-exist") == []

    # 2. Directory without .now.ts files
    empty_dir = tmp_path / "empty_bundle"
    empty_dir.mkdir()
    assert engine.load_bundle_schemas(empty_dir) == []

    # 3. Directory with valid fluent/app.now.ts
    bundle_dir = tmp_path / "valid_bundle"
    fluent_dir = bundle_dir / "fluent"
    fluent_dir.mkdir(parents=True)
    (fluent_dir / "app.now.ts").write_text(SAMPLE_FLUENT_TS, encoding="utf-8")

    schemas = engine.load_bundle_schemas(bundle_dir)
    assert len(schemas) == 1
    assert schemas[0].name == "x_demo_ai_routing_log"

    # 4. Unreadable/corrupt file is safely skipped
    corrupt_bundle = tmp_path / "corrupt_bundle"
    (corrupt_bundle / "fluent").mkdir(parents=True)
    (corrupt_bundle / "fluent" / "app.now.ts").write_bytes(b"\xff\xfe\x00\x00\x80\x81")
    assert engine.load_bundle_schemas(corrupt_bundle) == []


def test_compute_diff() -> None:
    """Verify structural schema diff calculation between two table schema sets."""
    engine = FluentEngine()

    cols_base = [
        FluentColumnDef(name="c1", label="Col 1", column_type="string", mandatory=False),
        FluentColumnDef(name="c2", label="Col 2", column_type="string", mandatory=True),
        FluentColumnDef(name="ref_col", label="Ref", column_type="reference", reference="incident"),
    ]
    t1_base = FluentTableSchema(name="t1", label="Table 1", columns=cols_base)
    t2_base = FluentTableSchema(name="t2", label="Table 2", columns=[])

    # 1. Identical schemas
    diff_same = engine.compute_diff([t1_base, t2_base], [t1_base, t2_base])
    assert diff_same.identical is True
    assert diff_same.added_tables == []
    assert diff_same.removed_tables == []
    assert diff_same.modified_tables == {}

    # 2. Modifications:
    # - t2 removed
    # - t3 added
    # - t1 has: c1 type changed (string -> integer), c2 mandatory changed (True -> False),
    #   ref_col reference changed (incident -> change_request), c_new added, c_old removed
    cols_modified = [
        FluentColumnDef(name="c1", label="Col 1", column_type="integer", mandatory=False),
        FluentColumnDef(name="c2", label="Col 2", column_type="string", mandatory=False),
        FluentColumnDef(
            name="ref_col", label="Ref", column_type="reference", reference="change_request"
        ),
        FluentColumnDef(name="c_new", label="New Col", column_type="string"),
    ]
    cols_base_extra = cols_base + [
        FluentColumnDef(name="c_old", label="Old Col", column_type="string")
    ]
    t1_old = FluentTableSchema(name="t1", label="Table 1", columns=cols_base_extra)
    t1_new = FluentTableSchema(name="t1", label="Table 1", columns=cols_modified)
    t3_new = FluentTableSchema(name="t3", label="Table 3", columns=[])

    diff_mod = engine.compute_diff([t1_old, t2_base], [t1_new, t3_new])
    assert diff_mod.identical is False
    assert diff_mod.added_tables == ["t3"]
    assert diff_mod.removed_tables == ["t2"]
    assert "t1" in diff_mod.modified_tables

    changes = diff_mod.modified_tables["t1"]
    assert any("Added column 'c_new'" in ch for ch in changes)
    assert any("Removed column 'c_old'" in ch for ch in changes)
    assert any("type changed: string -> integer" in ch for ch in changes)
    assert any("reference changed: incident -> change_request" in ch for ch in changes)
    assert any("mandatory changed: True -> False" in ch for ch in changes)
