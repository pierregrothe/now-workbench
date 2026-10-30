"""API routes for customization templates and parameterization."""

from typing import Any

from fastapi import APIRouter, HTTPException

from now_workbench.config.settings import settings
from now_workbench.db import (
    TemplateInstantiationRequest,
    TemplateRecord,
    db_session,
)
from now_workbench.templates import TemplateEngine

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[TemplateRecord])
def list_templates() -> list[TemplateRecord]:
    """List all available customization templates."""
    with db_session() as repo:
        return repo.list_templates()


@router.post("/{template_id}/instantiate")
def instantiate_template(template_id: str, req: TemplateInstantiationRequest) -> dict[str, Any]:
    """Instantiate a customization template with customer placeholders."""
    with db_session() as repo:
        templates = {t.id: t for t in repo.list_templates()}
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found.")

    engine = TemplateEngine(
        bundles_dir=settings.get_bundles_dir(), output_dir=settings.workspace_dir
    )
    base_id = templates[template_id].base_bundle_id
    try:
        output_dir = engine.instantiate(base_id, req)
        return {
            "success": True,
            "bundle_id": req.target_bundle_id,
            "customer_name": req.customer_name,
            "bundle_path": str(output_dir),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
