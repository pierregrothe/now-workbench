"""Demo bundle manager for packing, unpacking, discovering, and validating bundles."""

import json
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from now_workbench.domains.bundles.models import DemoBundleInfo, DemoManifest
from now_workbench.platform.config.paths import safe_child


class BundleManager:
    """Manages demonstration bundles in the local filesystem."""

    def __init__(self, storage_dir: Path) -> None:
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def list_bundles(self) -> list[DemoBundleInfo]:
        """Discover and load metadata for all installed demo bundles."""
        bundles: list[DemoBundleInfo] = []
        if not self.storage_dir.exists():
            return bundles

        for item in self.storage_dir.iterdir():
            if item.is_dir() and (item / "manifest.json").exists():
                try:
                    info = self.inspect_bundle(item)
                    bundles.append(info)
                except Exception:
                    continue
        return sorted(bundles, key=lambda b: b.manifest.name)

    def inspect_bundle(self, bundle_dir: Path) -> DemoBundleInfo:
        """Inspect and parse a bundle directory."""
        manifest_path = bundle_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest missing in {bundle_dir}")

        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not manifest_data.get("created_at"):
            manifest_data["created_at"] = datetime.fromtimestamp(
                manifest_path.stat().st_mtime, tz=UTC
            ).isoformat()
        manifest = DemoManifest.model_validate(manifest_data)

        fluent_files: list[str] = []
        fluent_dir = bundle_dir / "fluent"
        if fluent_dir.exists():
            fluent_files = [p.name for p in fluent_dir.glob("**/*.now.ts")]

        seed_files: list[str] = []
        seed_dir = bundle_dir / "seed"
        if seed_dir.exists():
            seed_files = [p.name for p in seed_dir.glob("*.json")]

        has_walkthrough = (bundle_dir / "walkthrough" / "guide.md").exists()

        sys_props: dict[str, str] = {}
        props_path = bundle_dir / "properties" / "sys_properties.json"
        if props_path.exists():
            try:
                sys_props = json.loads(props_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        media_captures: list[dict[str, Any]] = []
        caps_path = bundle_dir / "media" / "captures.json"
        if caps_path.exists():
            try:
                media_captures = json.loads(caps_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        return DemoBundleInfo(
            manifest=manifest,
            bundle_path=str(bundle_dir.resolve()),
            fluent_files=fluent_files,
            seed_files=seed_files,
            has_walkthrough=has_walkthrough,
            sys_properties=sys_props,
            media_captures=media_captures,
        )

    def export_bundle(self, bundle_id: str, output_archive: Path) -> Path:
        """Package a bundle directory into a portable .sn-demo.zip archive."""
        bundle_dir = safe_child(self.storage_dir, bundle_id)
        if not bundle_dir.exists():
            raise FileNotFoundError(f"Bundle {bundle_id} does not exist")

        output_archive.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in bundle_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(bundle_dir)
                    zf.write(file_path, arcname)
        return output_archive

    def import_bundle(self, archive_path: Path) -> DemoBundleInfo:
        """Extract a .sn-demo.zip archive into the storage directory."""
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive {archive_path} does not exist")

        with zipfile.ZipFile(archive_path, "r") as zf:
            namelist = zf.namelist()
            if "manifest.json" not in namelist:
                raise ValueError("Archive is missing required manifest.json at root")

            manifest_content = zf.read("manifest.json").decode("utf-8")
            manifest = DemoManifest.model_validate(json.loads(manifest_content))

            target_dir = safe_child(self.storage_dir, manifest.id)
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)

            zf.extractall(target_dir)

        return self.inspect_bundle(target_dir)

    def clone_bundle(
        self,
        source_id: str,
        target_id: str,
        target_name: str | None = None,
        source_root: Path | None = None,
    ) -> DemoBundleInfo:
        """Clone a bundle to customize without mutating the original.

        Args:
            source_id: Bundle to copy.
            target_id: Id of the new bundle (in this manager's storage).
            target_name: Display name; defaults to "<source name> (Cloned)".
            source_root: Bundles root holding the source (a shared snapshot); defaults to this
                manager's storage.
        """
        clean_target_id = target_id.strip().lower()
        if not clean_target_id:
            raise ValueError("Target bundle ID cannot be empty.")

        src_dir = safe_child(source_root or self.storage_dir, source_id)
        if not src_dir.exists() or not (src_dir / "manifest.json").exists():
            raise FileNotFoundError(f"Source bundle '{source_id}' does not exist.")

        target_dir = safe_child(self.storage_dir, clean_target_id)
        if target_dir.exists():
            raise FileExistsError(f"Target bundle '{clean_target_id}' already exists.")

        shutil.copytree(src_dir, target_dir)

        manifest_path = target_dir / "manifest.json"
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_data["id"] = clean_target_id
        if target_name and target_name.strip():
            manifest_data["name"] = target_name.strip()
        else:
            manifest_data["name"] = f"{manifest_data.get('name', source_id)} (Cloned)"

        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
        return self.inspect_bundle(target_dir)

    def delete_bundle(self, bundle_id: str) -> bool:
        """Delete a demonstration bundle artifact directory."""
        clean_id = bundle_id.strip()
        if not clean_id:
            raise ValueError("Bundle ID cannot be empty.")

        target_dir = safe_child(self.storage_dir, clean_id)
        if not target_dir.exists() or not target_dir.is_dir():
            raise FileNotFoundError(f"Demo bundle '{clean_id}' does not exist.")

        shutil.rmtree(target_dir)
        return True

    def update_bundle_manifest(
        self,
        bundle_id: str,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> DemoBundleInfo:
        """Update metadata fields in a bundle's manifest.json."""
        clean_id = bundle_id.strip()
        target_dir = safe_child(self.storage_dir, clean_id)
        if not target_dir.is_dir():
            raise FileNotFoundError(f"Demo bundle '{clean_id}' does not exist.")
        manifest_path = target_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json missing in '{clean_id}'.")
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if name is not None:
            data["name"] = name.strip()
        if description is not None:
            data["description"] = description.strip()
        if tags is not None:
            data["tags"] = [t.strip() for t in tags if t.strip()]
        manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return self.inspect_bundle(target_dir)
