"""Tests for declarative demo playbooks and PlaywrightPlaybookDriver."""

import json
from pathlib import Path

from now_workbench.domains.capture.driver import PlaywrightPlaybookDriver, load_playbook
from now_workbench.domains.capture.playbook import DemoPlaybook, PlaybookActionType, PlaybookStep
from now_workbench.domains.instances.models import InstanceRecord


def test_demo_playbook_model_validation() -> None:
    """Verify DemoPlaybook and PlaybookStep Pydantic v2 validation."""
    step = PlaybookStep(
        id="s1",
        action=PlaybookActionType.MOVE_AND_CLICK,
        description="Click incident",
        selector="#row-target-incident",
    )
    playbook = DemoPlaybook(
        bundle_id="test-bundle",
        title="Test Walkthrough",
        steps=[step],
    )
    assert playbook.bundle_id == "test-bundle"
    assert len(playbook.steps) == 1
    assert playbook.steps[0].action == PlaybookActionType.MOVE_AND_CLICK


def test_load_playbook_from_file_and_fallback(tmp_path: Path) -> None:
    """Verify load_playbook loads existing file or synthesizes default."""
    bundle_dir = tmp_path / "sample-bundle"
    walkthrough_dir = bundle_dir / "walkthrough"
    walkthrough_dir.mkdir(parents=True)

    # 1. Fallback when file doesn't exist
    fallback = load_playbook(bundle_dir, "sample-bundle")
    assert fallback.bundle_id == "sample-bundle"
    assert len(fallback.steps) >= 3

    # 2. Load from playbook.json
    custom = {
        "bundle_id": "sample-bundle",
        "title": "Custom Title",
        "start_path": "/custom.do",
        "steps": [
            {
                "id": "c1",
                "action": "navigate",
                "description": "Custom navigate",
                "path": "/custom.do",
            }
        ],
    }
    (walkthrough_dir / "playbook.json").write_text(json.dumps(custom), encoding="utf-8")
    loaded = load_playbook(bundle_dir, "sample-bundle")
    assert loaded.title == "Custom Title"
    assert loaded.steps[0].action == PlaybookActionType.NAVIGATE


async def test_playwright_playbook_driver_fake_mode(tmp_path: Path) -> None:
    """Verify PlaywrightPlaybookDriver runs deterministically in fake_mode."""
    driver = PlaywrightPlaybookDriver(data_dir=tmp_path / "data")
    playbook = DemoPlaybook(
        bundle_id="fake-bundle",
        title="Fake Demo",
        steps=[
            PlaybookStep(
                id="step-1",
                action=PlaybookActionType.AUTHENTICATE,
                description="Auth check",
            ),
            PlaybookStep(
                id="step-2",
                action=PlaybookActionType.MOVE_AND_CLICK,
                description="Click button",
                selector="#submit",
            ),
        ],
    )
    instance = InstanceRecord(
        id="inst-fake",
        name="Fake Instance",
        url="https://fake.service-now.com",
        username="admin",
        password="pwd",
        auth_type="basic",
        release="Xanadu",
        is_default=True,
    )

    out_video = tmp_path / "fake-bundle" / "media" / "proof.webm"
    out_image = tmp_path / "fake-bundle" / "media" / "proof.png"

    result = await driver.execute_playbook(
        playbook=playbook,
        instance=instance,
        output_video=out_video,
        output_image=out_image,
        fake_mode=True,
    )

    assert result.success is True
    assert result.total_steps == 2
    assert result.passed_steps == 2
    assert out_video.exists()
    assert out_image.exists()
    assert len(result.step_results) == 2
    assert result.step_results[0].status == "passed"
