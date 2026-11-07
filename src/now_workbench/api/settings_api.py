"""FastAPI routes for Now Workbench settings and preferences."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from now_workbench.ai.client import validate_api_key
from now_workbench.auth.guard import current_user, require_role
from now_workbench.auth.models import AuthUser, Role
from now_workbench.db.models import WorkbenchPreferences, WorkbenchPreferencesUpdate
from now_workbench.db.repos.preferences import PreferencesRepository
from now_workbench.db.session import db_session

_ADMIN_ONLY = [Depends(require_role(Role.ADMIN))]
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
    with db_session() as conn:
        return PreferencesRepository(conn).get_workbench_preferences()


@router.put("", response_model=WorkbenchPreferences)
async def update_workbench_settings(
    req: WorkbenchPreferencesUpdate, user: AuthUser = Depends(current_user)
) -> WorkbenchPreferences:
    """Update settings. Changing the Claude API key needs the admin role; other fields do not."""
    if req.anthropic_api_key is not None and Role.ADMIN not in user.roles:
        raise HTTPException(
            status_code=403, detail="Changing the Claude API key needs the admin role."
        )
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

    with db_session() as conn:
        try:
            return PreferencesRepository(conn).update_workbench_preferences(req)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@router.delete(
    "/api-key",
    response_model=WorkbenchPreferences,
    dependencies=_ADMIN_ONLY,
)
def delete_workbench_api_key() -> WorkbenchPreferences:
    """Explicitly delete the configured Claude AI API key."""
    with db_session() as conn:
        return PreferencesRepository(conn).delete_anthropic_api_key()


@router.post(
    "/validate-key",
    response_model=ValidateKeyResponse,
    dependencies=_ADMIN_ONLY,
)
async def validate_key_endpoint(req: ValidateKeyRequest) -> ValidateKeyResponse:
    """Perform a live probe validation of a candidate Claude API key."""
    valid, message = await validate_api_key(req.api_key)
    return ValidateKeyResponse(valid=valid, message=message)


@router.post("/reset", response_model=WorkbenchPreferences)
def reset_workbench_settings() -> WorkbenchPreferences:
    """Reset the signed-in person's settings to defaults (the shared Claude key stays)."""
    with db_session() as conn:
        return PreferencesRepository(conn).reset_workbench_preferences()
