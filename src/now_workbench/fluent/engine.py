"""ServiceNow Fluent SDK (*.now.ts) AST inspection, schema extraction, and diff engine."""

import re
from pathlib import Path

from now_workbench.fluent.models import (
    FluentColumnDef,
    FluentSchemaDiff,
    FluentTableSchema,
)


def _extract_string_param(block: str, key: str) -> str | None:
    """Extract a single- or double-quoted string parameter from a JS/TS object literal."""
    match = re.search(rf"""\b{key}\s*:\s*['"]([^'"]+)['"]""", block)
    return match.group(1).strip() if match else None


def _extract_bool_param(block: str, key: str) -> bool:
    """Extract boolean parameter from a JS/TS object literal."""
    match = re.search(rf"""\b{key}\s*:\s*(true|false)\b""", block, re.IGNORECASE)
    return match.group(1).lower() == "true" if match else False


def _extract_int_param(block: str, key: str) -> int | None:
    """Extract integer parameter from a JS/TS object literal."""
    match = re.search(rf"""\b{key}\s*:\s*(\d+)""", block)
    return int(match.group(1)) if match else None


def _parse_column_block(col_name: str, body: str) -> FluentColumnDef:
    """Parse property definitions within a column Record(...) or TypeColumn(...) call."""
    label = _extract_string_param(body, "label") or col_name
    ref = _extract_string_param(body, "reference")
    col_type = "reference" if ref else "string"
    mandatory = _extract_bool_param(body, "mandatory")
    max_len = _extract_int_param(body, "maxLength")

    return FluentColumnDef(
        name=col_name,
        label=label,
        column_type=col_type,
        reference=ref,
        mandatory=mandatory,
        max_length=max_len,
    )


def _parse_columns(content: str) -> list[FluentColumnDef]:
    """Parse column definitions out of a Table declaration."""
    columns: list[FluentColumnDef] = []
    col_pattern = re.compile(
        r"""([a-zA-Z0-9_]+)\s*:\s*(?:Record|[A-Za-z]+Column)\s*\(\s*\{([^}]*)\}\s*\)""",
        re.DOTALL,
    )
    for match in col_pattern.finditer(content):
        col_name = match.group(1)
        col_body = match.group(2)
        columns.append(_parse_column_block(col_name, col_body))
    return columns


def _parse_table_block(table_content: str) -> FluentTableSchema | None:
    """Parse a Table({ ... }) block into a FluentTableSchema."""
    name = _extract_string_param(table_content, "name")
    if not name:
        return None
    label = _extract_string_param(table_content, "label") or name
    columns = _parse_columns(table_content)

    return FluentTableSchema(
        name=name,
        label=label,
        columns=columns,
        raw_source=table_content.strip(),
    )


def _diff_columns(cols_a: list[FluentColumnDef], cols_b: list[FluentColumnDef]) -> list[str]:
    """Compare column definitions between two versions of a table."""
    changes: list[str] = []
    map_a = {c.name: c for c in cols_a}
    map_b = {c.name: c for c in cols_b}

    for name, c_b in map_b.items():
        if name not in map_a:
            changes.append(f"Added column '{name}' ({c_b.column_type})")
        else:
            c_a = map_a[name]
            if c_a.column_type != c_b.column_type:
                msg = f"Column '{name}' type changed: {c_a.column_type} -> {c_b.column_type}"
                changes.append(msg)
            if c_a.reference != c_b.reference:
                msg = f"Column '{name}' reference changed: {c_a.reference} -> {c_b.reference}"
                changes.append(msg)
            if c_a.mandatory != c_b.mandatory:
                msg = f"Column '{name}' mandatory changed: {c_a.mandatory} -> {c_b.mandatory}"
                changes.append(msg)

    for name in map_a:
        if name not in map_b:
            changes.append(f"Removed column '{name}'")

    return changes


def _extract_table_blocks(content: str) -> list[str]:
    """Extract Table({ ... }) blocks by scanning balanced braces."""
    blocks: list[str] = []
    pattern = re.compile(r"""\bTable\s*\(\s*\{""")
    for match in pattern.finditer(content):
        start_idx = match.start()
        brace_count = 0
        for i in range(match.end() - 1, len(content)):
            char = content[i]
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    close_paren = content.find(")", i)
                    end_idx = close_paren + 1 if close_paren != -1 else i + 1
                    blocks.append(content[start_idx:end_idx])
                    break
    return blocks


class FluentEngine:
    """Inspects ServiceNow Fluent SDK (*.now.ts) files and performs AST schema diffs."""

    def parse_source(self, content: str) -> list[FluentTableSchema]:
        """Extract all Table schemas declared in a Fluent TypeScript source."""
        schemas: list[FluentTableSchema] = []
        for block in _extract_table_blocks(content):
            parsed = _parse_table_block(block)
            if parsed:
                schemas.append(parsed)
        return schemas

    def load_bundle_schemas(self, bundle_path: Path) -> list[FluentTableSchema]:
        """Discover and parse all *.now.ts schema files within a demo bundle."""
        if not bundle_path.exists():
            return []

        schemas: list[FluentTableSchema] = []
        candidates = list(bundle_path.glob("**/*.now.ts"))
        for candidate in sorted(candidates):
            try:
                content = candidate.read_text(encoding="utf-8")
                schemas.extend(self.parse_source(content))
            except Exception:
                continue
        return schemas

    def compute_diff(
        self,
        schemas_a: list[FluentTableSchema],
        schemas_b: list[FluentTableSchema],
    ) -> FluentSchemaDiff:
        """Compute structural schema differences between two Fluent table sets."""
        map_a = {t.name: t for t in schemas_a}
        map_b = {t.name: t for t in schemas_b}

        added = [name for name in map_b if name not in map_a]
        removed = [name for name in map_a if name not in map_b]
        modified: dict[str, list[str]] = {}

        for name, t_a in map_a.items():
            if name in map_b:
                t_b = map_b[name]
                col_changes = _diff_columns(t_a.columns, t_b.columns)
                if col_changes:
                    modified[name] = col_changes

        is_identical = len(added) == 0 and len(removed) == 0 and len(modified) == 0
        return FluentSchemaDiff(
            added_tables=sorted(added),
            removed_tables=sorted(removed),
            modified_tables=modified,
            identical=is_identical,
        )
