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


def test_delete_bundle(tmp_path: Path) -> None:
    """Verify deleting a bundle removes directory and handles errors."""
    bundle_dir = tmp_path / "to-delete"
    bundle_dir.mkdir()
    manifest = DemoManifest(id="to-delete", name="To Delete", version="1.0.0")
    (bundle_dir / "manifest.json").write_text(manifest.model_dump_json(), encoding="utf-8")

    mgr = BundleManager(storage_dir=tmp_path)
    assert len(mgr.list_bundles()) == 1

    # Successfully delete
    res = mgr.delete_bundle("to-delete")
    assert res is True
    assert not bundle_dir.exists()
    assert len(mgr.list_bundles()) == 0

    # Deleting nonexistent bundle raises FileNotFoundError
    import pytest

    with pytest.raises(FileNotFoundError):
        mgr.delete_bundle("to-delete")

    with pytest.raises(ValueError):
        mgr.delete_bundle("")


def test_bundle_manager_error_handling(tmp_path: Path) -> None:
    """Verify error handling on corrupted, missing, or malformed bundles."""
    import zipfile

    import pytest

    mgr = BundleManager(storage_dir=tmp_path)

    # 1. Missing manifest in directory
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    with pytest.raises(FileNotFoundError, match="Manifest missing"):
        mgr.inspect_bundle(empty_dir)

    # 2. Export non-existent bundle
    with pytest.raises(FileNotFoundError, match="does not exist"):
        mgr.export_bundle("bundle-404", tmp_path / "out.zip")

    # 3. Import non-existent archive
    with pytest.raises(FileNotFoundError, match="does not exist"):
        mgr.import_bundle(tmp_path / "archive-404.zip")

    # 4. Import zip missing manifest.json
    bad_zip = tmp_path / "no_manifest.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("random.txt", "hello")
    with pytest.raises(ValueError, match="missing required manifest.json"):
        mgr.import_bundle(bad_zip)

    # 5. Malformed sys_properties.json handled gracefully
    prop_dir = tmp_path / "bundle_bad_props"
    prop_dir.mkdir()
    manifest_json = '{"id":"bad_props","name":"Bad Props","version":"1.0"}'
    (prop_dir / "manifest.json").write_text(manifest_json, encoding="utf-8")
    (prop_dir / "properties").mkdir()
    (prop_dir / "properties" / "sys_properties.json").write_text("invalid json", encoding="utf-8")
    info = mgr.inspect_bundle(prop_dir)
    assert info.sys_properties == {}

    # 6. list_bundles on non-existent storage directory returns empty list
    non_existent_mgr = BundleManager(storage_dir=tmp_path / "no_storage")
    non_existent_mgr.storage_dir.rmdir()
    assert non_existent_mgr.list_bundles() == []

    # 7. list_bundles skips unparseable directory
    corrupt_bundle = tmp_path / "corrupt_bundle"
    corrupt_bundle.mkdir()
    (corrupt_bundle / "manifest.json").write_text("not json", encoding="utf-8")
    assert any(b.manifest.id == "bad_props" for b in mgr.list_bundles())

    # 8. Import bundle overwrites existing target directory
    valid_zip = tmp_path / "valid_overwrite.zip"
    with zipfile.ZipFile(valid_zip, "w") as zf:
        zf.writestr("manifest.json", '{"id":"overwritten_bundle","name":"V1","version":"1.0"}')
    mgr.import_bundle(valid_zip)
    with zipfile.ZipFile(valid_zip, "w") as zf:
        zf.writestr("manifest.json", '{"id":"overwritten_bundle","name":"V2","version":"2.0"}')
    re_imported = mgr.import_bundle(valid_zip)
    assert re_imported.manifest.name == "V2"


def test_update_bundle_manifest(tmp_path: Path) -> None:
    """Verify updating bundle manifest metadata."""
    bundle_dir = tmp_path / "updatable-bundle"
    bundle_dir.mkdir()
    manifest = DemoManifest(
        id="updatable-bundle",
        name="Original Name",
        description="Original Description",
        tags=["initial"],
        version="1.0.0",
    )
    (bundle_dir / "manifest.json").write_text(manifest.model_dump_json(), encoding="utf-8")

    mgr = BundleManager(storage_dir=tmp_path)
    updated = mgr.update_bundle_manifest(
        bundle_id="updatable-bundle",
        name="Updated Name",
        description="Updated Description",
        tags=["updated", "demo"],
    )
    assert updated.manifest.name == "Updated Name"
    assert updated.manifest.description == "Updated Description"
    assert updated.manifest.tags == ["updated", "demo"]

    # Verify disk persistence
    re_inspected = mgr.inspect_bundle(bundle_dir)
    assert re_inspected.manifest.name == "Updated Name"
    assert re_inspected.manifest.description == "Updated Description"
    assert re_inspected.manifest.tags == ["updated", "demo"]
