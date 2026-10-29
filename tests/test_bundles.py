"""Tests for demo bundle manager."""

from pathlib import Path
from now_workbench.bundles.manager import BundleManager
from now_workbench.bundles.models import DemoManifest


def test_list_and_inspect_bundle(tmp_path: Path) -> None:
    # Set up sample bundle directory
    bundle_dir = tmp_path / "test-bundle"
    bundle_dir.mkdir(parents=True)
    (bundle_dir / "fluent").mkdir()
    (bundle_dir / "seed").mkdir()
    (bundle_dir / "properties").mkdir()
    (bundle_dir / "walkthrough").mkdir()

    manifest = DemoManifest(
        id="test-bundle",
        name="Test Incident App",
        version="1.0.0",
        sn_release="Xanadu",
    )
    (bundle_dir / "manifest.json").write_text(manifest.model_dump_json(), encoding="utf-8")
    (bundle_dir / "fluent" / "app.now.ts").write_text("// Fluent code", encoding="utf-8")
    (bundle_dir / "seed" / "01_data.json").write_text("[]", encoding="utf-8")
    (bundle_dir / "walkthrough" / "guide.md").write_text("# Guide", encoding="utf-8")

    mgr = BundleManager(storage_dir=tmp_path)
    bundles = mgr.list_bundles()

    assert len(bundles) == 1
    b = bundles[0]
    assert b.manifest.id == "test-bundle"
    assert b.manifest.name == "Test Incident App"
    assert len(b.fluent_files) == 1
    assert len(b.seed_files) == 1
    assert b.has_walkthrough is True


def test_export_and_import_bundle(tmp_path: Path) -> None:
    source_dir = tmp_path / "storage"
    source_dir.mkdir()
    bundle_dir = source_dir / "sample"
    bundle_dir.mkdir()
    manifest = DemoManifest(id="sample", name="Sample Export", version="2.0.0")
    (bundle_dir / "manifest.json").write_text(manifest.model_dump_json(), encoding="utf-8")

    mgr = BundleManager(storage_dir=source_dir)
    archive = tmp_path / "export.sn-demo.zip"
    mgr.export_bundle("sample", archive)
    assert archive.exists()

    # Import into a separate destination directory
    target_storage = tmp_path / "imported_storage"
    target_mgr = BundleManager(storage_dir=target_storage)
    imported = target_mgr.import_bundle(archive)

    assert imported.manifest.id == "sample"
    assert imported.manifest.name == "Sample Export"
