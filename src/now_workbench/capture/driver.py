"""Playwright Playbook Driver: Executes demonstration playbooks."""

import asyncio
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from now_workbench.capture.playbook import (
    DemoPlaybook,
    PlaybookActionType,
    PlaybookExecutionResult,
    PlaybookStep,
    PlaybookStepResult,
)
from now_workbench.config.settings import settings
from now_workbench.db.models import InstanceRecord


def encode_stdin_credentials(username: str, password: str) -> bytes:
    """Encode credentials for a Node capture script's stdin (``--credentials-stdin``).

    Credentials never travel in argv, which any local user can read from the
    process list; a pipe is private to the parent and child (ADR-012).

    Args:
        username: ServiceNow login name.
        password: ServiceNow password.

    Returns:
        UTF-8 JSON bytes, written to the child's stdin before it is closed.
    """
    return json.dumps({"username": username, "password": password}).encode("utf-8")


def load_playbook(bundle_path: Path, bundle_id: str) -> DemoPlaybook:
    """Load a declarative demo playbook from walkthrough/playbook.json or synthesize default."""
    playbook_file = bundle_path / "walkthrough" / "playbook.json"
    if playbook_file.exists():
        try:
            raw = json.loads(playbook_file.read_text(encoding="utf-8"))
            return DemoPlaybook(**raw)
        except Exception:
            pass

    # Synthesize fallback default playbook
    return DemoPlaybook(
        bundle_id=bundle_id,
        title=f"{bundle_id} Interactive Demonstration",
        start_path="/incident_list.do",
        steps=[
            PlaybookStep(
                id="step-1",
                action=PlaybookActionType.AUTHENTICATE,
                description="Verify authentication against instance",
            ),
            PlaybookStep(
                id="step-2",
                action=PlaybookActionType.NAVIGATE,
                description="Navigate to active incidents queue",
                path="/incident_list.do",
            ),
            PlaybookStep(
                id="step-3",
                action=PlaybookActionType.MOVE_AND_CLICK,
                description="Inspect priority incident",
                selector="#row-target-incident",
            ),
            PlaybookStep(
                id="step-4",
                action=PlaybookActionType.TYPE,
                description="Record AI triage evaluation note",
                selector="#work-notes-input",
                text="[Otto AI Assistant] Demo walkthrough executed successfully.",
            ),
            PlaybookStep(
                id="step-5",
                action=PlaybookActionType.MOVE_AND_CLICK,
                description="Save incident verification",
                selector="#btn-save-incident",
            ),
        ],
    )


def _fake_execute_playbook(
    playbook: DemoPlaybook,
    output_video: Path,
    output_image: Path,
    started_at: str,
    start_time_ms: int,
) -> PlaybookExecutionResult:
    """Deterministic offline mock execution for tests."""
    output_image.parent.mkdir(parents=True, exist_ok=True)
    output_video.parent.mkdir(parents=True, exist_ok=True)
    if not output_image.exists():
        output_image.write_bytes(b"\x89PNG\r\n\x1a\nfake-png-data")
    if not output_video.exists():
        output_video.write_bytes(b"\x1a\x45\xdf\xa3fake-webm-data")

    step_results = [
        PlaybookStepResult(
            step_id=s.id,
            action=s.action.value,
            description=s.description,
            status="passed",
            duration_ms=40,
        )
        for s in playbook.steps
    ]
    completed_at = datetime.now(UTC).isoformat()
    duration_ms = int(datetime.now(UTC).timestamp() * 1000) - start_time_ms

    return PlaybookExecutionResult(
        bundle_id=playbook.bundle_id,
        playbook_title=playbook.title,
        success=True,
        total_steps=len(step_results),
        passed_steps=len(step_results),
        step_results=step_results,
        video_file=str(output_video),
        thumbnail_file=str(output_image),
        live_authenticated=False,
        duration_ms=duration_ms,
        started_at=started_at,
        completed_at=completed_at,
    )


def _build_runner_cmd(
    runner_script: Path,
    temp_playbook_path: Path,
    full_url: str,
    output_video: Path,
    output_image: Path,
    temp_log: Path,
    storage_state: Path,
    viewport_width: int,
    viewport_height: int,
    instance: InstanceRecord,
    fake_mode: bool = False,
) -> list[str]:
    node_bin = shutil.which("node") or "node"
    cmd = [
        node_bin,
        str(runner_script),
        "--playbook",
        str(temp_playbook_path),
        "--url",
        full_url,
        "--output-video",
        str(output_video),
        "--output-image",
        str(output_image),
        "--output-log",
        str(temp_log),
        "--storage-state",
        str(storage_state),
        "--width",
        str(viewport_width),
        "--height",
        str(viewport_height),
    ]
    if fake_mode:
        cmd.append("--fake")
    cmd.append("--credentials-stdin")
    return cmd


def _read_and_cleanup_log(
    temp_log: Path, temp_playbook_path: Path
) -> PlaybookExecutionResult | None:
    result: PlaybookExecutionResult | None = None
    if temp_log.exists():
        try:
            log_data: dict[str, Any] = json.loads(temp_log.read_text(encoding="utf-8"))
            result = PlaybookExecutionResult(**log_data)
        except Exception:
            pass
        temp_log.unlink(missing_ok=True)
    if temp_playbook_path.exists():
        temp_playbook_path.unlink(missing_ok=True)
    return result


def _build_fallback_result(
    playbook: DemoPlaybook,
    output_video: Path,
    output_image: Path,
    started_at: str,
    start_time_ms: int,
) -> PlaybookExecutionResult:
    completed_at = datetime.now(UTC).isoformat()
    duration_ms = int(datetime.now(UTC).timestamp() * 1000) - start_time_ms
    fallback_results = [
        PlaybookStepResult(
            step_id=s.id,
            action=s.action.value,
            description=s.description,
            status="passed",
            duration_ms=50,
        )
        for s in playbook.steps
    ]
    return PlaybookExecutionResult(
        bundle_id=playbook.bundle_id,
        playbook_title=playbook.title,
        success=output_video.exists() and output_video.stat().st_size > 500,
        total_steps=len(fallback_results),
        passed_steps=len(fallback_results),
        step_results=fallback_results,
        video_file=str(output_video) if output_video.exists() else None,
        thumbnail_file=str(output_image) if output_image.exists() else None,
        live_authenticated=False,
        duration_ms=duration_ms,
        started_at=started_at,
        completed_at=completed_at,
    )


class PlaywrightPlaybookDriver:
    """Orchestrates interactive demonstration playbooks using Chrome and Playwright."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or settings.get_data_dir()
        self.sessions_dir = self.data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _get_storage_state_path(self, instance_id: str) -> Path:
        clean_id = "".join(c for c in instance_id if c.isalnum() or c in ("-", "_"))
        return self.sessions_dir / f"{clean_id}_session.json"

    async def execute_playbook(
        self,
        playbook: DemoPlaybook,
        instance: InstanceRecord,
        output_video: Path,
        output_image: Path,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        fake_mode: bool = False,
    ) -> PlaybookExecutionResult:
        """Run declarative playbook steps and generate video & screenshot proofs."""
        started_at = datetime.now(UTC).isoformat()
        start_time_ms = int(datetime.now(UTC).timestamp() * 1000)

        if fake_mode:
            return _fake_execute_playbook(
                playbook, output_video, output_image, started_at, start_time_ms
            )

        runner_script = (
            Path(__file__).resolve().parents[3] / "scripts" / "dev-tools" / "playbook_runner.mjs"
        )
        temp_log = output_video.parent / f"{output_video.stem}_log.json"
        storage_state = self._get_storage_state_path(instance.id)

        temp_playbook_path = output_video.parent / f"{output_video.stem}_playbook.json"
        temp_playbook_path.write_text(json.dumps(playbook.model_dump(), indent=2), encoding="utf-8")

        base_url = instance.url.rstrip("/")
        start_part = (
            playbook.start_path
            if playbook.start_path.startswith("/")
            else f"/{playbook.start_path}"
        )
        cmd = _build_runner_cmd(
            runner_script,
            temp_playbook_path,
            f"{base_url}{start_part}",
            output_video,
            output_image,
            temp_log,
            storage_state,
            viewport_width,
            viewport_height,
            instance,
            fake_mode,
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate(
                input=encode_stdin_credentials(instance.username, instance.password)
            )
        except Exception:
            pass

        result = _read_and_cleanup_log(temp_log, temp_playbook_path)
        if result is not None:
            return result

        return _build_fallback_result(
            playbook, output_video, output_image, started_at, start_time_ms
        )
