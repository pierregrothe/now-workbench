"""Global pytest fixtures ensuring complete database isolation from live data/workbench.db."""

from pathlib import Path

import pytest

from now_workbench.db import InstanceCreate, TemplateRecord, db_session


@pytest.fixture(autouse=True)
def isolate_workbench_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect WORKBENCH_DATA_DIR to an isolated temporary directory for every test."""
    data_dir = tmp_path / "workbench_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("WORKBENCH_DATA_DIR", str(data_dir))
    test_db = data_dir / "workbench.db"

    with db_session(test_db) as repo:
        repo.add_instance(
            InstanceCreate(
                id="default-instance",
                name="Primary ServiceNow Instance",
                url="fake://dev12345.service-now.com",
                username="admin",
                password="",
                auth_type="basic",
                release="Zurich",
                is_default=True,
            )
        )
        repo.save_template(
            TemplateRecord(
                id="agentic-router-template",
                name="GenAI Agentic Incident Router Template",
                description="Customizable AI routing and triage application for IT incidents",
                version="1.0.0",
                base_bundle_id="template-customer-service-ai",
                parameters_schema={
                    "customer_name": {"type": "string", "default": "Customer Corp"},
                    "primary_color": {"type": "string", "default": "#23a17e"},
                    "secondary_color": {"type": "string", "default": "#0284c7"},
                    "assignment_group": {"type": "string", "default": "IT Tier 1"},
                },
            )
        )

    return test_db
