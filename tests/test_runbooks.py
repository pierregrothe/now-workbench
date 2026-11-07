"""Tests for Walkthrough Runbook parsing, models, and stage verification."""

from pathlib import Path

import httpx
import pytest

from now_workbench.domains.instances.models import InstanceRecord
from now_workbench.domains.runbooks.engine import RunbookEngine
from now_workbench.domains.runbooks.models import DemoPersona, RunbookGuide, RunbookStage

SAMPLE_GUIDE_MD = """# Demonstration Guide: GenAI Agentic Incident Router

## Customer Value Narrative
In enterprise IT operations, high incident volume creates bottlenecks in Tier 1 triage.
This demonstration shows how ServiceNow Now Assist and custom Fluent automation routes
tickets with >90% accuracy in sub-seconds.

## Walkthrough Steps

1. **The Problem State**:
   - Impersonate **Beth Anglin** (`beth.anglin@example.com`).
   - Open unassigned IT incidents queue. Notice the backlog.

2. **The Autonomous Triage**:
   - Click "Simulate AI Intake Scan".
   - Show Now Assist extracting entities from the ticket description.
   - Point to `x_demo_ai_routing_log` populated automatically with confidence scores.

3. **Resolution Acceleration**:
   - Ticket #1 (VPN timeout) auto-categorized to Network Operations with priority elevated.
   - Show how resolution time drops from 45 minutes to under 2 minutes.
"""


def test_runbook_models() -> None:
    """Verify Runbook Pydantic model invariants and frozen immutability."""
    persona = DemoPersona(name="Beth Anglin", role="Triage Agent", email="beth@example.com")
    assert persona.name == "Beth Anglin"

    stage = RunbookStage(
        step_number=1,
        title="Problem State",
        persona="Beth Anglin",
        instructions=["Open incidents queue"],
        talking_points=["Notice the backlog"],
        target_table="incident",
    )
    assert stage.step_number == 1
    assert stage.target_table == "incident"

    guide = RunbookGuide(
        bundle_id="sample-ai-assistant",
        title="Incident Router",
        narrative="AI routing automation",
        stages=[stage],
        personas=[persona],
    )
    assert guide.bundle_id == "sample-ai-assistant"
    assert len(guide.stages) == 1
    assert len(guide.personas) == 1


def test_parse_markdown_complete() -> None:
    """Verify parsing a full markdown demonstration guide into structured stages."""
    engine = RunbookEngine()
    guide = engine.parse_markdown(SAMPLE_GUIDE_MD, bundle_id="sample-ai-assistant")

    assert guide.bundle_id == "sample-ai-assistant"
    assert "Incident Router" in guide.title
    assert "bottlenecks in Tier 1" in guide.narrative
    assert len(guide.stages) == 3

    # Stage 1 assertions
    s1 = guide.stages[0]
    assert s1.step_number == 1
    assert s1.title == "The Problem State"
    assert s1.persona == "Beth Anglin"
    assert len(s1.instructions) >= 1
    assert any("Impersonate" in inst for inst in s1.instructions)

    # Stage 2 assertions
    s2 = guide.stages[1]
    assert s2.step_number == 2
    assert s2.title == "The Autonomous Triage"
    assert s2.target_table == "x_demo_ai_routing_log"
    assert len(s2.talking_points) >= 1

    # Stage 3 assertions
    s3 = guide.stages[2]
    assert s3.step_number == 3
    assert s3.title == "Resolution Acceleration"
    assert len(s3.talking_points) >= 1

    # Personas extraction
    assert len(guide.personas) == 1
    assert guide.personas[0].name == "Beth Anglin"
    assert guide.personas[0].email == "beth.anglin@example.com"


def test_parse_markdown_edge_cases() -> None:
    """Verify parsing edge cases with unformatted, minimal, or empty markdown."""
    engine = RunbookEngine()

    # Empty content
    empty_guide = engine.parse_markdown("", bundle_id="empty-bundle")
    assert empty_guide.bundle_id == "empty-bundle"
    assert empty_guide.stages == []

    # Unnumbered or loose content with other section
    unstructured_md = """# Minimal Demo
Some text without standard sections.
## Other Information
Miscellaneous notes here.
## Walkthrough
1. First simple step without bold tags
- Just an action bullet
2. **With Inline Rest**: Direct inline rest instruction
-
- Non-table code block `somevar`
- Valid table `custom_table_log`
"""
    parsed = engine.parse_markdown(unstructured_md, bundle_id="mini")
    assert parsed.title == "Minimal Demo"
    assert len(parsed.stages) == 2
    assert parsed.stages[0].step_number == 1
    assert parsed.stages[0].title == "First simple step without bold tags"
    assert parsed.stages[1].step_number == 2
    assert parsed.stages[1].title == "With Inline Rest"
    assert "Direct inline rest instruction" in parsed.stages[1].instructions
    assert parsed.stages[1].target_table == "custom_table_log"


def test_load_runbook_from_filesystem(tmp_path: Path) -> None:
    """Verify loading guide.md from bundle directory structures."""
    engine = RunbookEngine()

    # 1. Non-existent path returns None
    assert engine.load_runbook(tmp_path / "does-not-exist") is None

    # 2. Path without guide.md returns None
    empty_dir = tmp_path / "empty_bundle"
    empty_dir.mkdir()
    assert engine.load_runbook(empty_dir) is None

    # 3. Path with walkthrough/guide.md
    bundle_dir = tmp_path / "valid_bundle"
    wt_dir = bundle_dir / "walkthrough"
    wt_dir.mkdir(parents=True)
    (wt_dir / "guide.md").write_text(SAMPLE_GUIDE_MD, encoding="utf-8")

    loaded = engine.load_runbook(bundle_dir)
    assert loaded is not None
    assert loaded.bundle_id == "valid_bundle"
    assert len(loaded.stages) == 3

    # 4. Corrupt unreadable guide.md returns None
    corrupt_dir = tmp_path / "corrupt_bundle"
    (corrupt_dir / "walkthrough").mkdir(parents=True)
    (corrupt_dir / "walkthrough" / "guide.md").write_bytes(b"\xff\xfe\x00\x00\x80\x81")
    assert engine.load_runbook(corrupt_dir) is None


@pytest.mark.asyncio
async def test_verify_stage_simulated_and_no_table() -> None:
    """Verify stage verification in fake_mode and when target_table is not set."""
    engine = RunbookEngine()
    inst = InstanceRecord(
        id="fake-inst",
        name="Fake Instance",
        url="fake://test.service-now.com",
    )

    # 1. Fake mode / fake scheme
    stage_table = RunbookStage(
        step_number=1,
        title="Scan",
        instructions=[],
        talking_points=[],
        target_table="incident",
    )
    ok, msg = await engine.verify_stage(stage_table, inst, fake_mode=True)
    assert ok is True
    assert "simulation mode" in msg

    # 2. Stage without target_table on a non-fake instance URL
    real_inst = InstanceRecord(
        id="real-inst",
        name="Real Instance",
        url="https://instance.service-now.com",
    )
    stage_no_table = RunbookStage(
        step_number=2,
        title="Overview",
        instructions=[],
        talking_points=[],
        target_table=None,
    )
    ok_no, msg_no = await engine.verify_stage(stage_no_table, real_inst, fake_mode=False)
    assert ok_no is True
    assert "no platform table checks required" in msg_no

    # 3. Default client execution when client=None
    fail_inst = InstanceRecord(
        id="fail-inst",
        name="Fail Instance",
        url="http://127.0.0.1:1",
    )
    ok_fail, msg_fail = await engine.verify_stage(
        stage_table, fail_inst, client=None, fake_mode=False
    )
    assert ok_fail is False
    assert "verification error" in msg_fail


@pytest.mark.asyncio
async def test_verify_stage_http_transport() -> None:
    """Verify live Table API HTTP query verification with in-memory mock transport."""
    engine = RunbookEngine()
    inst = InstanceRecord(
        id="http-inst",
        name="HTTP Instance",
        url="https://instance.service-now.com",
        username="admin",
        password="pwd",
        auth_type="basic",
    )
    stage = RunbookStage(
        step_number=1,
        title="Check Records",
        instructions=[],
        talking_points=[],
        target_table="x_demo_ai_routing_log",
        verification_query="^ORDERBYDESCsys_created_on",
    )

    # 1. HTTP 200 with records
    def handle_200_records(request: httpx.Request) -> httpx.Response:
        assert "x_demo_ai_routing_log" in str(request.url)
        assert "sysparm_limit=1" in str(request.url)
        return httpx.Response(200, json={"result": [{"sys_id": "123", "confidence": "0.95"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle_200_records)) as client:
        ok, msg = await engine.verify_stage(stage, inst, client=client, fake_mode=False)
        assert ok is True
        assert "records found" in msg

    # 2. HTTP 200 with empty list
    def handle_200_empty(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"result": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle_200_empty)) as client:
        ok, msg = await engine.verify_stage(stage, inst, client=client, fake_mode=False)
        assert ok is True
        assert "accessible" in msg

    # 3. HTTP 404 table not found
    def handle_404(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": {"message": "Invalid table"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle_404)) as client:
        ok, msg = await engine.verify_stage(stage, inst, client=client, fake_mode=False)
        assert ok is False
        assert "HTTP 404" in msg

    # 4. Connection error
    def handle_err(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Network timeout")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle_err)) as client:
        ok, msg = await engine.verify_stage(stage, inst, client=client, fake_mode=False)
        assert ok is False
        assert "verification error" in msg
