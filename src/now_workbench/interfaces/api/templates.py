"""API routes for customization templates and parameterization."""

from typing import Any

from fastapi import APIRouter, HTTPException

from now_workbench.domains.templates import (
    TemplateEngine,
    TemplateInstantiationRequest,
    TemplateRecord,
    TemplateRepository,
)
from now_workbench.platform.config.settings import settings
from now_workbench.platform.db.session import db_session

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[TemplateRecord])
def list_templates() -> list[TemplateRecord]:
    """List all available customization templates."""
    with db_session() as conn:
        return TemplateRepository(conn).list_templates()


@router.post("/{template_id}/instantiate")
def instantiate_template(template_id: str, req: TemplateInstantiationRequest) -> dict[str, Any]:
    """Instantiate a customization template with customer placeholders."""
    with db_session() as conn:
        templates = {t.id: t for t in TemplateRepository(conn).list_templates()}
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
