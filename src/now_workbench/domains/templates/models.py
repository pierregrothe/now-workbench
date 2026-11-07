# src/now_workbench/domains/templates/models.py
# Customization templates and their instantiation request.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Template models."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "TemplateInstantiationRequest",
    "TemplateRecord",
]


class TemplateRecord(BaseModel):
    """Reusable customization template with customer placeholders."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    description: str
    version: str = "1.0.0"
    base_bundle_id: str
    parameters_schema: dict[str, Any] = Field(default_factory=dict)


class TemplateInstantiationRequest(BaseModel):
    """Request to instantiate a customization template for a customer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_bundle_id: str
    customer_name: str
    primary_color: str = "#23a17e"
    secondary_color: str = "#0284c7"
    logo_url: str = ""
    assignment_group: str = "IT Support Tier 1"
