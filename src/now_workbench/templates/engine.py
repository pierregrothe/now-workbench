"""Template engine for parameterizing and instantiating ServiceNow customization bundles."""

import json
import re
import shutil
from pathlib import Path

from now_workbench.db.models import TemplateInstantiationRequest


class TemplateEngine:
    """Instantiates customized demo bundles from templates with customer placeholders."""

    def __init__(self, bundles_dir: Path, output_dir: Path) -> None:
        self.bundles_dir = bundles_dir
        self.output_dir = output_dir

    def instantiate(
        self,
        base_bundle_id: str,
        request: TemplateInstantiationRequest,
    ) -> Path:
        """Create a new customized bundle directory with customer placeholder substitution."""
        source_dir = self.bundles_dir / base_bundle_id
        if not source_dir.exists():
            raise FileNotFoundError(f"Base bundle '{base_bundle_id}' not found.")

        target_dir = self.output_dir / request.target_bundle_id
        if target_dir.exists():
            shutil.rmtree(target_dir)

        # Copy base bundle structure
        shutil.copytree(source_dir, target_dir)

        # Clean customer identifier for code/identifiers
        clean_name = re.sub(r"[^a-zA-Z0-9_]", "_", request.customer_name.lower())

        replacements = {
            "{{customer_name}}": request.customer_name,
            "{{customer_name_clean}}": clean_name,
            "{{primary_color}}": request.primary_color,
            "{{secondary_color}}": request.secondary_color,
            "{{logo_url}}": request.logo_url,
            "{{assignment_group}}": request.assignment_group,
        }

        # Substitute placeholders in text files
        for file_path in target_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix in (
                ".json",
                ".ts",
                ".js",
                ".md",
                ".txt",
            ):
                content = file_path.read_text(encoding="utf-8")
                modified = content
                for placeholder, val in replacements.items():
                    modified = modified.replace(placeholder, val)

                # Special handling for manifest.json
                if file_path.name == "manifest.json":
                    try:
                        manifest_data = json.loads(modified)
                        manifest_data["id"] = request.target_bundle_id
                        manifest_data["name"] = (
                            f"{request.customer_name} - {manifest_data.get('name', 'Custom App')}"
                        )
                        modified = json.dumps(manifest_data, indent=2) + "\n"
                    except Exception:
                        pass

                file_path.write_text(modified, encoding="utf-8")

        return target_dir
