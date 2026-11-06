"""Async Playwright runner for capturing ServiceNow screenshots and videos."""

import asyncio
import base64
import json
import shutil
import struct
import uuid
import zlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from now_workbench.capture.driver import (
    PlaywrightPlaybookDriver,
    encode_stdin_credentials,
    load_playbook,
)
from now_workbench.capture.models import CaptureArtifact, CaptureRequest
from now_workbench.config.paths import safe_child
from now_workbench.db.models import InstanceRecord
from now_workbench.releases import translate_workspace_url

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
    width: int,
    height: int,
    username: str = "",
    password: str = "",
    duration: float = 3.0,
    fake_mode: bool = False,
) -> bool:
    """Execute live Chrome / Puppeteer screenshot or WebM video capture."""
    script_path = (
        Path(__file__).resolve().parents[3] / "scripts" / "dev-tools" / "chrome_capture.mjs"
    )
    if not script_path.exists():
        return False
    node_bin = shutil.which("node")
    if not node_bin:
        return False
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
        str(width),
        "--height",
        str(height),
        "--duration",
        str(duration),
    ]
    if fake_mode:
        cmd.append("--fake")
    cmd.append("--credentials-stdin")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate(input=encode_stdin_credentials(username, password))
        return proc.returncode == 0 and output_file.exists() and output_file.stat().st_size > 500
    except Exception:
        return False


async def _run_playwright_cli(
    full_url: str, output_file: Path, width: int, height: int, wait_timeout_ms: int = 1500
) -> bool:
    """Execute Playwright screenshot capture via async subprocess."""
    npx_bin = shutil.which("npx")
    if not npx_bin:
        return False
    cmd = [
        npx_bin,
        "playwright",
        "screenshot",
        f"--viewport-size={width},{height}",
        f"--wait-for-timeout={wait_timeout_ms}",
        full_url,
        str(output_file),
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    return proc.returncode == 0 and output_file.exists()


async def _execute_video_playbook(
    bundle_path: Path,
    bundle_id: str,
    instance_id: str | None,
    base_url: str,
    username: str,
    password: str,
    output_file: Path,
    thumb_file: Path,
    width: int,
    height: int,
    fake_mode: bool,
) -> tuple[bool, bool, list[dict[str, Any]]]:
    """Execute declarative demo playbook for video proof recording."""
    driver = PlaywrightPlaybookDriver()
    playbook = load_playbook(bundle_path, bundle_id)
    inst_record = InstanceRecord(
        id=instance_id or "default-instance",
        name="Target Instance",
        url=base_url,
        username=username or "admin",
        password=password,
        auth_type="basic",
        release="Xanadu",
        is_default=True,
        status="active",
    )
    exec_res = await driver.execute_playbook(
        playbook,
        inst_record,
        output_video=output_file,
        output_image=thumb_file,
        viewport_width=width,
        viewport_height=height,
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
        wait_timeout_ms: int = 1500,
        username: str = "",
        password: str = "",
        release: str = "Xanadu",
    ) -> CaptureArtifact:
        """Capture a screenshot or video of the target ServiceNow instance."""
        capture_id = f"cap-{uuid.uuid4().hex[:8]}"
        ext = "webm" if req.media_type == "video" else "png"
        filename = f"{capture_id}.{ext}"
        media_dir = self._media_dir(req.bundle_id)
        output_file = media_dir / filename

        base_url = instance_url.rstrip("/")
        raw_path = req.target_path if req.target_path.startswith("/") else f"/{req.target_path}"
        path_part = translate_workspace_url(raw_path, release)
        full_url = f"{base_url}{path_part}"

        used_engine = "playwright-simulated"
        step_results: list[dict[str, Any]] = []
        live_auth = False

        if not req.fake_mode:
            if req.media_type == "video":
                ok, live_auth, step_results = await _execute_video_playbook(
                    safe_child(self.bundles_dir, req.bundle_id),
                    req.bundle_id,
                    req.instance_id,
                    base_url,
                    username,
                    password,
                    output_file,
                    media_dir / f"{capture_id}.png",
                    req.viewport_width,
                    req.viewport_height,
                    fake_mode=False,
                )
                if ok:
                    used_engine = "google-chrome-native"
            else:
                chrome_ok = await _run_chrome_capture(
                    full_url,
                    output_file,
                    req.media_type,
                    req.viewport_width,
                    req.viewport_height,
                    username=username,
                    password=password,
                    fake_mode=req.fake_mode,
                )
                if chrome_ok:
                    used_engine = "google-chrome-native"
                else:
                    ok = await _run_playwright_cli(
                        full_url,
                        output_file,
                        req.viewport_width,
                        req.viewport_height,
                        wait_timeout_ms,
                    )
                    if ok:
                        used_engine = "playwright-chromium"

        if not output_file.exists():
            if not req.fake_mode:
                sim_ok = await _run_chrome_capture(
                    full_url,
                    output_file,
                    req.media_type,
                    req.viewport_width,
                    req.viewport_height,
                    fake_mode=True,
                )
                if sim_ok:
                    used_engine = "playwright-simulated"
            if not output_file.exists():
                payload = _PLACEHOLDER_WEBM if ext == "webm" else _generate_simulated_png()
                output_file.write_bytes(payload)

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
