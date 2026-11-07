"""Template repository."""

import json

from now_workbench.domains.templates.models import TemplateRecord
from now_workbench.platform.db.repository import Repository


class TemplateRepository(Repository):
    """Repository for customization template persistence."""

    def list_templates(self) -> list[TemplateRecord]:
        """Return all available customization templates."""
        cursor = self.conn.execute(
            """
            SELECT id, name, description, version, base_bundle_id, parameters_schema
            FROM templates;
            """
        )
        templates: list[TemplateRecord] = []
        for row in cursor.fetchall():
            schema = json.loads(row["parameters_schema"]) if row["parameters_schema"] else {}
            templates.append(
                TemplateRecord(
                    id=row["id"],
                    name=row["name"],
                    description=row["description"],
                    version=row["version"],
                    base_bundle_id=row["base_bundle_id"],
                    parameters_schema=schema,
                )
            )
        return templates

    def save_template(self, tmpl: TemplateRecord) -> TemplateRecord:
        """Persist or update a customization template."""
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO templates (id, name, description, version, base_bundle_id,
                                       parameters_schema)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    version=excluded.version,
                    base_bundle_id=excluded.base_bundle_id,
                    parameters_schema=excluded.parameters_schema;
                """,
                (
                    tmpl.id,
                    tmpl.name,
                    tmpl.description,
                    tmpl.version,
                    tmpl.base_bundle_id,
                    json.dumps(tmpl.parameters_schema),
                ),
            )
        return tmpl
