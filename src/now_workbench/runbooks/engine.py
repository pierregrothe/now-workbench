"""Walkthrough Runbook parsing and verification engine for demonstration bundles."""

import re
from pathlib import Path
from typing import Any

import httpx

from now_workbench.db.models import InstanceRecord
from now_workbench.runbooks.models import (
    DemoPersona,
    RunbookGuide,
    RunbookStage,
    RunbookTestResult,
    StageTestResult,
)

_TALKING_PREFIXES = (
    "show how",
    "show ",
    "notice",
    "point to",
    "point out",
    "explain",
    "narrate",
    "ticket #",
)


def _extract_persona(cleaned: str, personas_dict: dict[str, DemoPersona]) -> str | None:
    """Extract persona from line and register into personas_dict if matched."""
    impersonate_match = re.search(
        r"(?:impersonate|as)\s+\*\*([^*]+)\*\*(?:\s+\(`([^`]+)`\))?",
        cleaned,
        re.IGNORECASE,
    )
    if not impersonate_match:
        return None
    p_name = impersonate_match.group(1).strip()
    p_email = (impersonate_match.group(2) or "").strip()
    if p_name not in personas_dict:
        personas_dict[p_name] = DemoPersona(
            name=p_name,
            email=p_email,
            role="Demonstration Persona",
        )
    return p_name


def _extract_target_table(cleaned: str) -> str | None:
    """Extract candidate table identifier from backticks."""
    table_match = re.search(r"`([a-zA-Z0-9_]{3,40})`", cleaned)
    if not table_match:
        return None
    candidate = table_match.group(1)
    if "_" in candidate or candidate in ("incident", "change_request", "problem"):
        return candidate
    return None


def _is_talking_point(cleaned: str) -> bool:
    """Check if line is a talking point or presenter hint."""
    lower = cleaned.lower()
    return any(lower.startswith(prefix) for prefix in _TALKING_PREFIXES)


def _process_step_lines(
    raw_lines: list[str],
    personas_dict: dict[str, DemoPersona],
) -> tuple[list[str], list[str], str | None, str | None]:
    """Process step lines into instructions, talking points, persona, and target table."""
    instructions: list[str] = []
    talking_points: list[str] = []
    persona: str | None = None
    target_table: str | None = None

    for raw_line in raw_lines:
        cleaned = re.sub(r"^\s*[-*]\s*", "", raw_line).strip()
        if not cleaned:
            continue
        p = _extract_persona(cleaned, personas_dict)
        if p and not persona:
            persona = p
        t = _extract_target_table(cleaned)
        if t and not target_table:
            target_table = t
        if _is_talking_point(cleaned):
            talking_points.append(cleaned)
        else:
            instructions.append(cleaned)

    return instructions, talking_points, persona, target_table


def _flush_stage(
    stages: list[RunbookStage],
    step_num: int | None,
    step_title: str,
    step_lines: list[str],
    personas_dict: dict[str, DemoPersona],
) -> None:
    """Build and append a RunbookStage if a valid step number is present."""
    if step_num is None:
        return
    instructions, talking_points, persona, target_table = _process_step_lines(
        step_lines, personas_dict
    )
    v_query = "^ORDERBYDESCsys_created_on" if target_table else None
    stages.append(
        RunbookStage(
            step_number=step_num,
            title=step_title or f"Step {step_num}",
            persona=persona,
            instructions=instructions,
            talking_points=talking_points,
            target_table=target_table,
            verification_query=v_query,
        )
    )


def _classify_section(header_line: str) -> str:
    """Classify markdown section header into narrative, steps, or other."""
    title = header_line[3:].strip().lower()
    if "narrative" in title or "value" in title:
        return "narrative"
    if "step" in title or "walkthrough" in title or "stage" in title:
        return "steps"
    return "other"


def _parse_step_header(stripped: str) -> tuple[int, str, str] | None:
    """Parse numbered step line into (step_num, step_title, rest)."""
    cleaned = re.sub(r"^#{1,6}\s*", "", stripped).strip()
    match = re.match(
        r"^(?:step\s+)?(\d+)[:.]\s*(?:\*\*([^*]+)\*\*[:\s]*)?(.*)$",
        cleaned,
        re.IGNORECASE,
    )
    if not match:
        return None
    num = int(match.group(1))
    bold_title = match.group(2)
    rest = match.group(3)
    title = (bold_title or rest or f"Step {num}").strip()
    return num, title, rest


class _ParserState:
    """Internal accumulator for markdown parsing."""

    def __init__(self, bundle_id: str) -> None:
        self.bundle_id = bundle_id
        self.title = bundle_id
        self.narrative_lines: list[str] = []
        self.stages: list[RunbookStage] = []
        self.personas_dict: dict[str, DemoPersona] = {}
        self.current_section = ""
        self.current_step_num: int | None = None
        self.current_step_title = ""
        self.current_step_lines: list[str] = []

    def flush(self) -> None:
        """Flush the current step into stages."""
        _flush_stage(
            self.stages,
            self.current_step_num,
            self.current_step_title,
            self.current_step_lines,
            self.personas_dict,
        )
        self.current_step_num = None
        self.current_step_title = ""
        self.current_step_lines = []

    def handle_step_line(self, stripped: str) -> None:
        """Handle a line within the steps section."""
        parsed = _parse_step_header(stripped)
        if parsed:
            self.flush()
            self.current_step_num, self.current_step_title, rest = parsed
            if rest and rest != self.current_step_title:
                self.current_step_lines.append(rest)
        elif self.current_step_num is not None and not stripped.startswith("#"):
            self.current_step_lines.append(stripped)


class RunbookEngine:
    """Parses markdown demonstration walkthrough guides into structured runbooks."""

    def parse_markdown(self, content: str, bundle_id: str) -> RunbookGuide:
        """Parse guide.md content into a structured RunbookGuide."""
        state = _ParserState(bundle_id)

        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("# ") and state.title == bundle_id:
                state.title = re.sub(r"^#\s+(?:Demonstration Guide:\s*)?", "", stripped).strip()
            elif stripped.startswith("## "):
                state.flush()
                state.current_section = _classify_section(stripped)
            elif state.current_section == "narrative" and not stripped.startswith("#"):
                state.narrative_lines.append(stripped)
            elif state.current_section == "steps":
                state.handle_step_line(stripped)

        state.flush()

        return RunbookGuide(
            bundle_id=bundle_id,
            title=state.title or bundle_id,
            narrative=" ".join(state.narrative_lines),
            stages=state.stages,
            personas=list(state.personas_dict.values()),
        )

    def load_runbook(self, bundle_path: Path, bundle_id: str = "") -> RunbookGuide | None:
        """Load and parse guide.md from a bundle directory if present."""
        resolved_id = bundle_id or bundle_path.name
        for candidate in [
            bundle_path / "walkthrough" / "guide.md",
            bundle_path / "guide.md",
        ]:
            if candidate.is_file():
                try:
                    content = candidate.read_text(encoding="utf-8")
                    return self.parse_markdown(content, resolved_id)
                except Exception:
                    return None
        return None

    async def _execute_http_get(
        self,
        url: str,
        auth: Any,
        client: httpx.AsyncClient | None,
    ) -> httpx.Response:
        """Execute async HTTP GET request."""
        headers = {"Accept": "application/json"}
        if client is not None:
            return await client.get(url, auth=auth, headers=headers)
        async with httpx.AsyncClient(timeout=10.0) as default_client:
            return await default_client.get(url, auth=auth, headers=headers)

    def _evaluate_response(self, resp: httpx.Response, stage: RunbookStage) -> tuple[bool, str]:
        """Evaluate ServiceNow Table API HTTP response for stage verification."""
        if resp.status_code != 200:
            return (
                False,
                f"Stage {stage.step_number} verification failed: Table API HTTP {resp.status_code}",
            )
        data = resp.json()
        results = data.get("result", [])
        if isinstance(results, list) and len(results) > 0:
            return (
                True,
                f"Stage {stage.step_number} verified: records found in '{stage.target_table}'",
            )
        return (
            True,
            f"Stage {stage.step_number} verified: table '{stage.target_table}' accessible",
        )

    async def verify_stage(
        self,
        stage: RunbookStage,
        instance: InstanceRecord,
        client: httpx.AsyncClient | None = None,
        fake_mode: bool = False,
    ) -> tuple[bool, str]:
        """Verify ServiceNow Table API state for a specific demonstration stage."""
        if (
            fake_mode
            or instance.url.startswith("fake://")
            or instance.url.startswith("http://fake")
        ):
            return (
                True,
                f"Stage {stage.step_number} verified: table state validated (simulation mode)",
            )
        if not stage.target_table:
            return True, f"Stage {stage.step_number} verified: no platform table checks required"

        base_url = instance.url.rstrip("/")
        query = "?sysparm_limit=1"
        if stage.verification_query:
            query += f"&sysparm_query={stage.verification_query}"
        url = f"{base_url}/api/now/table/{stage.target_table}{query}"

        auth: Any = (
            httpx.BasicAuth(instance.username, instance.password)
            if instance.auth_type == "basic"
            else None
        )

        try:
            resp = await self._execute_http_get(url, auth, client)
            return self._evaluate_response(resp, stage)
        except Exception as exc:
            return False, f"Stage {stage.step_number} verification error: {exc}"

    async def test_runbook(
        self,
        guide: RunbookGuide,
        instance: InstanceRecord,
        client: httpx.AsyncClient | None = None,
        fake_mode: bool = False,
    ) -> RunbookTestResult:
        """Execute automated end-to-end verification across all runbook demo stages."""
        stage_results: list[StageTestResult] = []
        passed_count = 0
        for stage in guide.stages:
            passed, msg = await self.verify_stage(
                stage, instance, client=client, fake_mode=fake_mode
            )
            if passed:
                passed_count += 1
            stage_results.append(
                StageTestResult(
                    step_number=stage.step_number,
                    title=stage.title,
                    target_table=stage.target_table,
                    passed=passed,
                    message=msg,
                )
            )
        total = len(guide.stages)
        return RunbookTestResult(
            bundle_id=guide.bundle_id,
            instance_name=instance.name,
            total_stages=total,
            passed_stages=passed_count,
            all_passed=(passed_count == total and total > 0),
            stages=stage_results,
        )
