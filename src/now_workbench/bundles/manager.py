"""Demo bundle manager for packing, unpacking, discovering, and validating bundles."""

import json
import shutil
import zipfile
from pathlib import Path
from typing import Sequence

from now_workbench.bundles.models import DemoBundleInfo, DemoManifest


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

        return DemoBundleInfo(
            manifest=manifest,
            bundle_path=str(bundle_dir.resolve()),
            fluent_files=fluent_files,
            seed_files=seed_files,
            has_walkthrough=has_walkthrough,
            sys_properties=sys_props,
        )

    def export_bundle(self, bundle_id: str, output_archive: Path) -> Path:
        """Package a bundle directory into a portable .sn-demo.zip archive."""
        bundle_dir = self.storage_dir / bundle_id
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

            target_dir = self.storage_dir / manifest.id
            if target_dir.exists():
                shutil.rmtree(target_dir)
            target_dir.mkdir(parents=True, exist_ok=True)

            zf.extractall(target_dir)

        return self.inspect_bundle(target_dir)
