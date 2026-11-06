# src/now_workbench/sharing/store.py
# Immutable artifact snapshots on disk: one zip per version, extracted read-only on demand.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Snapshot store (ADR-018).

Layout under the data directory::

    artifact-versions/<id>/v<n>.zip        the frozen bundle
    published/<id>/v<n>/<id>/              extracted copy recipients read

The extra ``<id>`` level makes ``published/<id>/v<n>`` usable as a bundles root, so engines
that take ``(bundles_dir, bundle_id)`` work on a snapshot unchanged.
"""

import shutil
import zipfile
from pathlib import Path

from now_workbench.config.paths import safe_child
from now_workbench.config.settings import settings

__all__ = ["delete_artifact_files", "published_root", "snapshot_bundle"]


def _versions_dir(artifact_id: str) -> Path:
    return safe_child(settings.get_data_dir() / "artifact-versions", artifact_id)


def _published_dir(artifact_id: str) -> Path:
    return safe_child(settings.get_data_dir() / "published", artifact_id)


def snapshot_bundle(bundle_dir: Path, artifact_id: str, version: int) -> int:
    """Freeze ``bundle_dir`` as version ``version`` of ``artifact_id``.

    Args:
        bundle_dir: The owner's working directory.
        artifact_id: The artifact (bundle) id.
        version: The version number being saved.

    Returns:
        The size of the snapshot archive in bytes.

    Raises:
        FileExistsError: That version was already frozen.
    """
    target = _versions_dir(artifact_id) / f"v{version}.zip"
    if target.exists():
        raise FileExistsError(f"Version {version} of '{artifact_id}' already exists.")
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".zip.partial")
    with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(bundle_dir.rglob("*")):
            if file_path.is_file() and not file_path.is_symlink():
                zf.write(file_path, file_path.relative_to(bundle_dir))
    partial.replace(target)
    return target.stat().st_size


def published_root(artifact_id: str, version: int) -> Path:
    """Return a bundles root holding ``artifact_id`` exactly as frozen in ``version``.

    Raises:
        FileNotFoundError: The version was never frozen.
    """
    root = _published_dir(artifact_id) / f"v{version}"
    bundle = root / artifact_id
    if (bundle / "manifest.json").exists():
        return root
    archive = _versions_dir(artifact_id) / f"v{version}.zip"
    if not archive.exists():
        raise FileNotFoundError(f"Version {version} of '{artifact_id}' is missing.")
    staging = root.with_name(f"v{version}.partial")
    shutil.rmtree(staging, ignore_errors=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(staging / artifact_id)
    shutil.rmtree(root, ignore_errors=True)
    staging.replace(root)
    return root


def delete_artifact_files(artifact_id: str) -> None:
    """Remove every snapshot and published copy of an artifact."""
    shutil.rmtree(_versions_dir(artifact_id), ignore_errors=True)
    shutil.rmtree(_published_dir(artifact_id), ignore_errors=True)
