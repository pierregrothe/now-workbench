# tests/test_deepfix_bundle_paths.py
# Regression tests: BundleManager must never address paths outside its storage dir
# Author: Pierre Grothe
# Date: 2026-11-06

import json
import zipfile
from pathlib import Path

import pytest

from now_workbench.bundles.manager import BundleManager
from now_workbench.config.paths import UnsafePathError


def _make_bundle(root: Path, bundle_id: str) -> None:
    d = root / bundle_id
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(
        json.dumps({"id": bundle_id, "name": bundle_id, "version": "1.0.0"}), encoding="utf-8"
    )


@pytest.fixture
def layout(tmp_path: Path) -> tuple[BundleManager, Path, Path]:
    storage = tmp_path / "bundles"
    mgr = BundleManager(storage_dir=storage)
    sentinel = tmp_path / "sentinel"
    sentinel.mkdir()
    (sentinel / "keep.txt").write_text("x", encoding="utf-8")
    return mgr, storage, sentinel


def test_delete_bundle_dotdot_is_rejected_and_parent_kept(
    layout: tuple[BundleManager, Path, Path],
) -> None:
    mgr, storage, sentinel = layout
    with pytest.raises(UnsafePathError):
        mgr.delete_bundle("..")
    assert (sentinel / "keep.txt").exists()
    assert storage.exists()


def test_delete_bundle_traversal_to_sibling_is_rejected(
    layout: tuple[BundleManager, Path, Path],
) -> None:
    mgr, _, sentinel = layout
    with pytest.raises(UnsafePathError):
        mgr.delete_bundle("../sentinel")
    assert (sentinel / "keep.txt").exists()


def test_clone_bundle_traversal_target_is_rejected(
    layout: tuple[BundleManager, Path, Path],
) -> None:
    mgr, storage, sentinel = layout
    _make_bundle(storage, "src")
    with pytest.raises(UnsafePathError):
        mgr.clone_bundle("src", "../escaped")
    assert not (sentinel.parent / "escaped").exists()


def test_clone_bundle_traversal_source_is_rejected(
    layout: tuple[BundleManager, Path, Path],
) -> None:
    mgr, _, sentinel = layout
    (sentinel / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(UnsafePathError):
        mgr.clone_bundle("../sentinel", "copy")


def test_export_bundle_traversal_id_is_rejected(
    layout: tuple[BundleManager, Path, Path], tmp_path: Path
) -> None:
    mgr, _, _ = layout
    with pytest.raises(UnsafePathError):
        mgr.export_bundle("../sentinel", tmp_path / "out.zip")


def test_update_bundle_manifest_traversal_id_is_rejected(
    layout: tuple[BundleManager, Path, Path],
) -> None:
    mgr, _, _ = layout
    with pytest.raises(UnsafePathError):
        mgr.update_bundle_manifest("../sentinel", name="x")


def test_import_bundle_traversal_manifest_id_is_rejected_before_extracting(
    layout: tuple[BundleManager, Path, Path], tmp_path: Path
) -> None:
    mgr, _, sentinel = layout
    archive = tmp_path / "evil.sn-demo.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(
            "manifest.json",
            json.dumps({"id": "../sentinel", "name": "evil", "version": "1.0.0"}),
        )
        zf.writestr("payload.txt", "pwned")
    with pytest.raises(UnsafePathError):
        mgr.import_bundle(archive)
    assert (sentinel / "keep.txt").exists()
    assert not (sentinel / "payload.txt").exists()


def test_clone_bundle_valid_ids_still_work(layout: tuple[BundleManager, Path, Path]) -> None:
    mgr, storage, _ = layout
    _make_bundle(storage, "src")
    info = mgr.clone_bundle("src", "Copy-1")
    assert info.manifest.id == "copy-1"
    assert (storage / "copy-1" / "manifest.json").exists()


def test_import_bundle_valid_archive_still_works(
    layout: tuple[BundleManager, Path, Path], tmp_path: Path
) -> None:
    mgr, storage, _ = layout
    archive = tmp_path / "ok.sn-demo.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("manifest.json", json.dumps({"id": "ok", "name": "ok", "version": "1.0.0"}))
    info = mgr.import_bundle(archive)
    assert info.manifest.id == "ok"
    assert (storage / "ok").is_dir()
