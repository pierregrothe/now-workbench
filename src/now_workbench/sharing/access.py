# src/now_workbench/sharing/access.py
# The one place that decides whether the signed-in person may read or change a demo bundle.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Bundle access resolution (ADR-018).

The owner works on the live directory; recipients of an approved share read the frozen snapshot
of the newest version approved for them; everyone else gets "not found", so the existence of
another person's bundle is never revealed.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from now_workbench.auth.models import LOCAL_EMAIL
from now_workbench.auth.owner import current_owner
from now_workbench.config.paths import safe_child
from now_workbench.config.settings import settings
from now_workbench.db.repository import DatabaseRepository
from now_workbench.sharing.models import AccessKind, ArtifactVersion
from now_workbench.sharing.store import published_root, snapshot_bundle

__all__ = [
    "BundleAccess",
    "ReadOnlyBundleError",
    "list_accessible",
    "register_new_bundle",
    "resolve_bundle",
    "save_version",
    "sync_registry",
]


class ReadOnlyBundleError(PermissionError):
    """A recipient tried to change a shared bundle."""


@dataclass(frozen=True)
class BundleAccess:
    """Where a bundle lives for this person and how they reach it.

    Attributes:
        artifact_id: The bundle id.
        root: A bundles directory that contains ``artifact_id`` (pass it to engines).
        kind: Owner (live directory) or shared (frozen snapshot).
        version: Newest saved version (owner) or the approved version (shared); 0 when none.
        owner: The owner's email.
    """

    artifact_id: str
    root: Path
    kind: AccessKind
    version: int
    owner: str

    @property
    def path(self) -> Path:
        """The bundle directory itself."""
        return self.root / self.artifact_id


def _manifest(bundle_dir: Path) -> dict[str, object]:
    data = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def save_version(
    repo: DatabaseRepository, artifact_id: str, note: str, created_by: str
) -> ArtifactVersion:
    """Freeze the live bundle as its next version.

    Args:
        repo: Open repository.
        artifact_id: The bundle id.
        note: What changed, in the owner's words.
        created_by: Who saved it.

    Returns:
        The new version.
    """
    bundle_dir = safe_child(settings.get_bundles_dir(), artifact_id)
    manifest = _manifest(bundle_dir)
    number = repo.next_artifact_version(artifact_id)
    size = snapshot_bundle(bundle_dir, artifact_id, number)
    return repo.add_artifact_version(
        artifact_id,
        name=str(manifest.get("name") or artifact_id),
        description=str(manifest.get("description") or ""),
        note=note,
        size_bytes=size,
        created_by=created_by,
    )


def register_new_bundle(repo: DatabaseRepository, artifact_id: str, owner: str) -> None:
    """Record a just-created bundle as ``owner``'s and freeze it as version 1."""
    repo.register_artifact(artifact_id, owner)
    save_version(repo, artifact_id, note="Created", created_by=owner)


def sync_registry(repo: DatabaseRepository, operator: str) -> int:
    """Register bundles found on disk without an owner (shipped samples, CLI imports).

    Args:
        repo: Open repository.
        operator: Who gets them: the first administrator, the local operator, or "" (claimed
            by the first administrator at setup).

    Returns:
        How many bundles were registered.
    """
    known = repo.artifact_owners()
    bundles_dir = settings.get_bundles_dir()
    if not bundles_dir.exists():
        return 0
    added = 0
    for item in sorted(bundles_dir.iterdir()):
        if item.name in known or not (item / "manifest.json").exists():
            continue
        register_new_bundle(repo, item.name, operator)
        added += 1
    return added


def _sync_if_local(repo: DatabaseRepository) -> None:
    """In local mode (one person, no Access) new bundles on disk are simply theirs.

    Behind Access this never runs per request: a directory created a moment before its
    creator registers it must not be claimed by someone else. There, start-up and the CLI
    register unowned bundles to the operator.
    """
    if not settings.get_access_audience():
        sync_registry(repo, LOCAL_EMAIL)


def resolve_bundle(repo: DatabaseRepository, artifact_id: str, write: bool = False) -> BundleAccess:
    """Return how the signed-in person reaches a bundle.

    Args:
        repo: Open repository.
        artifact_id: The bundle id.
        write: True for operations that change the bundle (owner only).

    Returns:
        The access record.

    Raises:
        LookupError: Not theirs and not shared with them (or it does not exist).
        ReadOnlyBundleError: Shared with them, but ``write`` was requested.
    """
    _sync_if_local(repo)
    email = current_owner()
    bundles_dir = settings.get_bundles_dir()
    working = safe_child(bundles_dir, artifact_id)
    owner = repo.artifact_owner(artifact_id)
    if owner == email and working.is_dir():
        versions = repo.list_artifact_versions(artifact_id)
        latest = versions[0].version if versions else 0
        return BundleAccess(artifact_id, bundles_dir, AccessKind.OWNER, latest, email)
    approved = repo.shared_with(email, repo.active_group_ids(email)).get(artifact_id)
    if approved is None or owner is None:
        raise LookupError(f"Demo bundle '{artifact_id}' was not found.")
    if write:
        raise ReadOnlyBundleError(
            f"'{artifact_id}' is shared with you read-only. Clone it to make your own copy."
        )
    return BundleAccess(
        artifact_id, published_root(artifact_id, approved), AccessKind.SHARED, approved, owner
    )


def list_accessible(repo: DatabaseRepository) -> list[BundleAccess]:
    """Return the signed-in person's own bundles and those shared with them."""
    _sync_if_local(repo)
    email = current_owner()
    bundles_dir = settings.get_bundles_dir()
    out: list[BundleAccess] = []
    for artifact_id, owner in sorted(repo.artifact_owners().items()):
        if owner == email and (bundles_dir / artifact_id).is_dir():
            versions = repo.list_artifact_versions(artifact_id)
            latest = versions[0].version if versions else 0
            out.append(BundleAccess(artifact_id, bundles_dir, AccessKind.OWNER, latest, email))
    shared = repo.shared_with(email, repo.active_group_ids(email))
    owners = repo.artifact_owners()
    for artifact_id, version in sorted(shared.items()):
        out.append(
            BundleAccess(
                artifact_id,
                published_root(artifact_id, version),
                AccessKind.SHARED,
                version,
                owners.get(artifact_id, ""),
            )
        )
    return out
