# src/now_workbench/domains/capture/engine.py
# Screenshots and walkthrough videos of an instance, filed in a demo bundle's media index.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Async Playwright runner for capturing ServiceNow screenshots and videos."""

import base64
import json
import shutil
import struct
import uuid
import zlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from now_workbench.domains.capture.driver import (
    PlaywrightPlaybookDriver,
    encode_stdin_credentials,
    load_playbook,
)
from now_workbench.domains.capture.models import CaptureArtifact, CaptureRequest, SignIn, Viewport
from now_workbench.domains.capture.playbook import DemoPlaybook
from now_workbench.domains.instances import InstanceRecord
from now_workbench.domains.releases import is_release_detected, translate_workspace_url
from now_workbench.platform.config.paths import dev_script, safe_child
from now_workbench.platform.procs import ProcessTimeoutError, communicate_bounded, spawn

__all__ = ["CaptureFailedError", "PlaywrightCaptureEngine", "UnknownReleaseError"]

# A screenshot signs in, loads a list and waits for it; anything slower is stuck.
_CAPTURE_TIMEOUT_S = 240.0

_HEADER = [3, 45, 66]  # ServiceNow header (#032d42)
_NAV = [11, 31, 48]  # Nav rail (#0b1f30)
_TOOLBAR = [248, 250, 252]  # Toolbar (#f8fafc)
_DIVIDER = [226, 232, 240]  # Divider (#e2e8f0)
_PILL = [98, 216, 78]  # Green pill badge (#62d84e)
_PRIMARY_TEXT = [71, 85, 105]  # Primary text (#475569)
_SECONDARY_TEXT = [148, 163, 184]  # Secondary text (#94a3b8)
_WHITE = [255, 255, 255]  # Canvas background


def _grid_element_pixel(x: int, row_y: int) -> list[int]:
    """Return color for elements inside a table grid row."""
    if row_y >= 18:
        return _WHITE
    if x < 150:
        return _PILL
    if 170 < x < 350:
        return _PRIMARY_TEXT
    if 380 < x < 550:
        return _SECONDARY_TEXT
    return _WHITE


def _simulated_pixel(x: int, y: int) -> list[int]:
    """Return RGB color for simulated ServiceNow preview pixel."""
    if y < 40:
        return _HEADER
    if x < 50:
        return _NAV
    if y < 80:
        return _TOOLBAR
    if (y - 80) % 36 < 2:
        return _DIVIDER
    if 90 < y < 400:
        return _grid_element_pixel(x, (y - 90) % 36)
    return _WHITE


def _generate_simulated_png(width: int = 800, height: int = 450) -> bytes:
    """Generate a clean, high-resolution simulated ServiceNow UI preview image."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            raw.extend(_simulated_pixel(x, y))
    compressed = zlib.compress(bytes(raw), level=6)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )


# Minimal valid 1-second VP8 WebM video for playable offline/simulated video captures
_PLACEHOLDER_WEBM = base64.b64decode(
    "GkXfo59ChoEBQveBAULygQRC84EIQoKEd2VibUKHgQJChYECGFOAZ+4VSalmjyrXsYQAD0JARImERHoAABZU"
    "rmudrpvXgQFzxYEBg4EBhoVWX1ZQOOCIsIIAQLqCAEAfQ7Z1s+eBAKOugQAAgBACAJ0BKkAAQAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
)


async def _run_chrome_capture(
    full_url: str,
    output_file: Path,
    media_type: str,
    viewport: Viewport,
    sign_in: SignIn | None = None,
    settle_ms: int = 1500,
) -> tuple[bool, str]:
    """Take a live Chrome (Puppeteer) screenshot or video.

    Args:
        full_url: Page to open.
        output_file: Where the script writes the capture.
        media_type: "screenshot" or "video".
        viewport: Browser viewport.
        sign_in: Credentials, sent on stdin.
        settle_ms: How long the page settles after loading, before the shot.

    Returns:
        (ok, why it failed); the reason is empty on success.
    """
    creds = sign_in or SignIn()
    script_path = dev_script("chrome_capture.mjs")
    if not script_path.exists():
        return False, f"the capture script is not installed ({script_path})"
    node_bin = shutil.which("node")
    if not node_bin:
        return False, "Node.js is not installed on the server"
    cmd = [
        node_bin,
        str(script_path),
        "--url",
        full_url,
        "--output",
        str(output_file),
        "--mode",
        media_type,
        "--width",
        str(viewport.width),
        "--height",
        str(viewport.height),
        "--settle-ms",
        str(settle_ms),
        "--credentials-stdin",
    ]
    try:
        proc = await spawn(cmd, stdin=True)
        _out, err = await communicate_bounded(
            proc, _CAPTURE_TIMEOUT_S, encode_stdin_credentials(creds.username, creds.password)
        )
    except ProcessTimeoutError as exc:  # before OSError: TimeoutError is an OSError
        return False, f"the browser {exc}"
    except OSError as exc:
        return False, f"could not start the browser: {exc}"
    if proc.returncode == 0 and output_file.exists() and output_file.stat().st_size > 500:
        return True, ""
    detail = err.decode("utf-8", "replace").strip().splitlines()
    return False, (detail[-1] if detail else f"the browser exited with code {proc.returncode}")


def _rooted(path: str) -> str:
    """Return ``path`` with exactly one leading slash; a full URL is returned as is."""
    return path if path.startswith(("http://", "https://")) else "/" + path.lstrip("/")


def _translate(path: str, release: str) -> str:
    """Root a path, then translate it for ``release``; an undetected release only roots it.

    Args:
        path: Requested path, possibly with an ``@workspace/...`` token or a full URL.
        release: The instance's detected release.

    Returns:
        The release-specific path with exactly one leading slash (a full URL keeps its
        form), or the rooted ``path`` untranslated when the release is not known (it is
        never guessed, ADR-014).
    """
    rooted = _rooted(path)
    if not is_release_detected(release):
        return rooted
    # A rooted token ("/@workspace/itsm/x") translates to "//now/..."; root it again.
    return _rooted(translate_workspace_url(rooted, release))


def _translated_playbook(playbook: DemoPlaybook, release: str) -> DemoPlaybook:
    """Return the playbook with its start path and step paths translated for ``release``."""
    steps = [
        step.model_copy(update={"path": _translate(step.path, release)}) if step.path else step
        for step in playbook.steps
    ]
    start = _translate(playbook.start_path, release)
    return playbook.model_copy(update={"start_path": start, "steps": steps})


def _playbook_instance(
    instance_id: str | None, base_url: str, sign_in: SignIn, release: str
) -> InstanceRecord:
    """The instance record a recorded walkthrough signs in to."""
    return InstanceRecord(
        id=instance_id or "default-instance",
        name="Target Instance",
        url=base_url,
        username=sign_in.username or "admin",
        password=sign_in.password,
        auth_type="basic",
        release=release,
        is_default=True,
        status="active",
    )


async def _execute_video_playbook(
    req: CaptureRequest,
    playbook: DemoPlaybook,
    instance: InstanceRecord,
    output_file: Path,
    thumb_file: Path,
    fake_mode: bool = False,
) -> tuple[bool, bool, list[dict[str, Any]]]:
    """Record the bundle's declarative walkthrough as the video proof."""
    driver = PlaywrightPlaybookDriver()
    exec_res = await driver.execute_playbook(
        playbook,
        instance,
        output_video=output_file,
        output_image=thumb_file,
        viewport=Viewport(width=req.viewport_width, height=req.viewport_height),
        fake_mode=fake_mode,
    )
    ok = exec_res.success and output_file.exists() and output_file.stat().st_size > 500
    steps = [s.model_dump() for s in exec_res.step_results]
    return ok, exec_res.live_authenticated, steps


def _delete_companion_files(media_dir: Path, filename: str) -> None:
    """Clean up companion thumbnail or related files sharing same stem."""
    stem = Path(filename).stem
    for companion in media_dir.glob(f"{stem}.*"):
        if companion.name != "captures.json" and companion.is_file():
            companion.unlink()


def _is_matching_capture(artifact: CaptureArtifact, filename: str, stem: str) -> bool:
    return (
        artifact.filename == filename
        or artifact.id == filename
        or Path(artifact.filename).stem == stem
    )


def _check_capture_exists(
    media_dir: Path, filename: str, stem: str, n_remaining: int, n_existing: int
) -> bool:
    if n_remaining < n_existing or (media_dir / filename).exists():
        return True
    matches = [m for m in media_dir.glob(f"{stem}.*") if m.name != "captures.json"]
    return len(matches) > 0


class CaptureFailedError(RuntimeError):
    """A live capture failed; nothing was saved (never replaced by a placeholder)."""


class UnknownReleaseError(CaptureFailedError):
    """A live capture was refused: the instance's release is not detected yet (ADR-014)."""


class PlaywrightCaptureEngine:
    """Captures screenshots and videos from a ServiceNow instance into a demo bundle."""

    def __init__(self, bundles_dir: Path) -> None:
        self.bundles_dir = bundles_dir

    def _media_dir(self, bundle_id: str) -> Path:
        media_dir = safe_child(self.bundles_dir, bundle_id) / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        return media_dir

    def list_captures(self, bundle_id: str) -> list[CaptureArtifact]:
        """Return all recorded screenshot and video captures for a bundle."""
        index_file = self._media_dir(bundle_id) / "captures.json"
        if not index_file.exists():
            return []
        raw = json.loads(index_file.read_text(encoding="utf-8"))
        return [CaptureArtifact(**item) for item in raw]

    def _save_capture_metadata(self, artifact: CaptureArtifact) -> None:
        existing = self.list_captures(artifact.bundle_id)
        updated = [artifact.model_dump(), *[a.model_dump() for a in existing]]
        index_file = self._media_dir(artifact.bundle_id) / "captures.json"
        index_file.write_text(json.dumps(updated, indent=2), encoding="utf-8")

    def delete_capture(self, bundle_id: str, filename: str) -> bool:
        """Delete a recorded screenshot or video capture and remove it from captures.json."""
        if not filename or "/" in filename or "\\" in filename or ".." in filename:
            raise ValueError(f"Invalid capture filename: {filename}")
        media_dir = self._media_dir(bundle_id)
        stem = Path(filename).stem
        target_file = media_dir / filename
        existing = self.list_captures(bundle_id)
        remaining = [a for a in existing if not _is_matching_capture(a, filename, stem)]
        if not _check_capture_exists(media_dir, filename, stem, len(remaining), len(existing)):
            raise FileNotFoundError(f"Capture file '{filename}' not found in '{bundle_id}'.")
        if target_file.exists():
            target_file.unlink()
        _delete_companion_files(media_dir, filename)
        index_file = media_dir / "captures.json"
        index_file.write_text(
            json.dumps([a.model_dump() for a in remaining], indent=2), encoding="utf-8"
        )
        return True

    def clear_all_captures(self, bundle_id: str) -> int:
        """Delete all recorded screenshot and video captures for a bundle."""
        if not bundle_id or "/" in bundle_id or "\\" in bundle_id or ".." in bundle_id:
            raise ValueError(f"Invalid bundle ID: {bundle_id}")
        media_dir = self._media_dir(bundle_id)
        count = 0
        for item in media_dir.glob("*"):
            if item.is_file() and item.name != "captures.json":
                if item.suffix.lower() in (".png", ".webm", ".json", ".jpg", ".jpeg"):
                    item.unlink()
                    count += 1
        index_file = media_dir / "captures.json"
        index_file.write_text("[]\n", encoding="utf-8")
        return count

    def update_capture(self, bundle_id: str, filename: str, label: str) -> CaptureArtifact:
        """Update label/caption of an existing capture artifact in captures.json."""
        if not filename or "/" in filename or "\\" in filename or ".." in filename:
            raise ValueError(f"Invalid capture filename: {filename}")
        existing = self.list_captures(bundle_id)
        target: CaptureArtifact | None = None
        updated_list: list[dict[str, Any]] = []
        for art in existing:
            if art.filename == filename:
                target = art.model_copy(update={"label": label.strip()})
                updated_list.append(target.model_dump())
            else:
                updated_list.append(art.model_dump())
        if not target:
            raise FileNotFoundError(f"Capture artifact '{filename}' not found in '{bundle_id}'.")
        index_file = self._media_dir(bundle_id) / "captures.json"
        index_file.write_text(json.dumps(updated_list, indent=2), encoding="utf-8")
        return target

    async def capture(
        self,
        req: CaptureRequest,
        instance_url: str,
        *,
        release: str,
        wait_timeout_ms: int = 1500,
        username: str = "",
        password: str = "",
    ) -> CaptureArtifact:
        """Capture a screenshot or video of the target ServiceNow instance.

        A screenshot opens ``req.target_path``; a video replays the bundle's walkthrough and
        records the playbook's start path. Paths are translated for ``release``.

        Args:
            req: What to capture and where to file it.
            instance_url: Base URL of the instance.
            release: The instance's detected release (``InstanceRecord.release``).
            wait_timeout_ms: How long a screenshot's page settles before the shot.
            username: Sign-in user, sent to the browser on stdin.
            password: Sign-in password, sent to the browser on stdin.

        Returns:
            The saved index entry.

        Raises:
            UnknownReleaseError: A live capture whose release is undetected (paths are never
                translated for a guessed release, ADR-014); a ``CaptureFailedError``.
            CaptureFailedError: The live capture failed.
        """
        if not req.fake_mode and not is_release_detected(release):
            raise UnknownReleaseError(
                "The instance's release is unknown, so its workspace paths cannot be chosen; "
                "run a connection test on the instance first (ADR-014)."
            )
        capture_id = f"cap-{uuid.uuid4().hex[:8]}"
        ext = "webm" if req.media_type == "video" else "png"
        filename = f"{capture_id}.{ext}"
        media_dir = self._media_dir(req.bundle_id)
        output_file = media_dir / filename

        base_url = instance_url.rstrip("/")
        playbook: DemoPlaybook | None = None
        if req.media_type == "video":
            bundle_path = safe_child(self.bundles_dir, req.bundle_id)
            playbook = _translated_playbook(load_playbook(bundle_path, req.bundle_id), release)
            path_part = playbook.start_path
        else:
            path_part = _translate(req.target_path, release)

        used_engine = "playwright-simulated"
        step_results: list[dict[str, Any]] = []
        live_auth = False

        if req.fake_mode:
            # Simulation was asked for explicitly: a placeholder, labelled as simulated.
            output_file.write_bytes(
                _PLACEHOLDER_WEBM if ext == "webm" else _generate_simulated_png()
            )
        elif playbook is not None:
            ok, live_auth, step_results = await _execute_video_playbook(
                req,
                playbook,
                _playbook_instance(
                    req.instance_id, base_url, SignIn(username=username, password=password), release
                ),
                output_file,
                media_dir / f"{capture_id}.png",
            )
            if not ok:
                failed = [
                    f"{s.get('description', '')} ({s.get('error_message') or s.get('status')})"
                    for s in step_results
                    if s.get("status") == "failed"
                ]
                raise CaptureFailedError(
                    "The video could not be recorded" + (f": {failed[0]}" if failed else ".")
                )
            used_engine = "google-chrome-native"
        else:
            ok, reason = await _run_chrome_capture(
                f"{base_url}{path_part}",
                output_file,
                req.media_type,
                Viewport(width=req.viewport_width, height=req.viewport_height),
                SignIn(username=username, password=password),
                settle_ms=wait_timeout_ms,
            )
            if not ok:
                raise CaptureFailedError(f"The screenshot could not be taken: {reason}.")
            used_engine = "google-chrome-native"

        artifact = CaptureArtifact(
            id=capture_id,
            bundle_id=req.bundle_id,
            instance_url=base_url,
            target_path=path_part,
            media_type=req.media_type,
            label=req.label,
            filename=filename,
            file_path=str(output_file),
            url=f"/api/demos/{req.bundle_id}/captures/{filename}",
            engine=used_engine,
            created_at=datetime.now(UTC).isoformat(),
            live_authenticated=live_auth,
            step_results=step_results,
        )
        self._save_capture_metadata(artifact)
        return artifact
