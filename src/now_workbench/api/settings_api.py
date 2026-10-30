"""FastAPI routes for Now Workbench settings and preferences."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from now_workbench.ai.client import validate_api_key
from now_workbench.db.models import WorkbenchPreferences, WorkbenchPreferencesUpdate
from now_workbench.db.session import db_session

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ValidateKeyRequest(BaseModel):
    """Payload for verifying an Anthropic Claude API key."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    api_key: str = Field(..., description="Claude API key to probe")


class ValidateKeyResponse(BaseModel):
    """Validation response with status flag and explanation message."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    valid: bool
    message: str


@router.get("", response_model=WorkbenchPreferences)
def get_workbench_settings() -> WorkbenchPreferences:
    """Return current Now Workbench settings and preferences."""
    with db_session() as repo:
        return repo.get_workbench_preferences()


@router.put("", response_model=WorkbenchPreferences)
async def update_workbench_settings(req: WorkbenchPreferencesUpdate) -> WorkbenchPreferences:
    """Update Now Workbench settings (with key pre-validation and delete-before-replace check)."""
    if req.anthropic_api_key is not None:
        key_to_check = req.anthropic_api_key.strip()
        if key_to_check and "..." not in key_to_check:
            # Validate key with Anthropic API probe
            valid, msg = await validate_api_key(key_to_check)
            if not valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Claude API key verification failed: {msg}",
                )

    with db_session() as repo:
        try:
            return repo.update_workbench_preferences(req)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/api-key", response_model=WorkbenchPreferences)
def delete_workbench_api_key() -> WorkbenchPreferences:
    """Explicitly delete the configured Claude AI API key."""
    with db_session() as repo:
        return repo.delete_anthropic_api_key()


@router.post("/validate-key", response_model=ValidateKeyResponse)
async def validate_key_endpoint(req: ValidateKeyRequest) -> ValidateKeyResponse:
    """Perform a live probe validation of a candidate Claude API key."""
    valid, message = await validate_api_key(req.api_key)
    return ValidateKeyResponse(valid=valid, message=message)


@router.post("/reset", response_model=WorkbenchPreferences)
def reset_workbench_settings() -> WorkbenchPreferences:
    """Reset Now Workbench settings back to defaults."""
    with db_session() as repo:
        return repo.reset_workbench_preferences()
