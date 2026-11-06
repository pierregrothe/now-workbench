# src/now_workbench/api/profile.py
# REST routes for the local profile: details, avatar, email-code approval, mail settings.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Profile API. The SMTP password and code hash never leave the backend."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from now_workbench.db import DatabaseRepository, db_session
from now_workbench.db.repos.profile import SMTP_PASSWORD_SECRET
from now_workbench.profile.avatars import (
    MAX_AVATAR_BYTES,
    PRESET_AVATARS,
    delete_avatar,
    load_avatar,
    save_avatar,
    sniff_image,
)
from now_workbench.profile.mailer import Mailer, MailError, SmtpMailer
from now_workbench.profile.models import (
    AvatarPublic,
    CodeConfirm,
    MailSettingsPublic,
    MailSettingsUpdate,
    PresetRequest,
    ProfilePublic,
    ProfileRecord,
    ProfileUpdate,
)
from now_workbench.profile.service import (
    CodeExpiredError,
    CooldownError,
    MailNotConfiguredError,
    NoEmailError,
    NoPendingCodeError,
    TooManyAttemptsError,
    VerificationError,
    WrongCodeError,
    confirm_code,
    send_code,
)
from now_workbench.profile.verification import CODE_TTL

__all__ = ["MailerFactory", "mailer_factory", "router"]

router = APIRouter(prefix="/api/profile", tags=["profile"])

type MailerFactory = Callable[[DatabaseRepository], Mailer]


def mailer_factory() -> MailerFactory:
    """Return the factory that builds the SMTP mailer from saved settings (tests override this)."""

    def build(repo: DatabaseRepository) -> Mailer:
        return SmtpMailer(repo.get_mail_settings(), repo.get_secret(SMTP_PASSWORD_SECRET))

    return build


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _public(repo: DatabaseRepository, record: ProfileRecord) -> ProfilePublic:
    url = (
        f"/api/profile/avatar?v={record.avatar_updated_at}"
        if record.avatar_kind == "upload"
        else None
    )
    return ProfilePublic(
        display_name=record.display_name,
        email=record.email,
        email_verified=record.email_verified_at is not None,
        avatar=AvatarPublic(kind=record.avatar_kind, preset=record.avatar_preset, url=url),
        verification_pending=record.code_hash is not None,
        mail_configured=repo.get_mail_settings().configured,
    )


@router.get("", response_model=ProfilePublic)
def get_profile() -> ProfilePublic:
    """Return the local profile."""
    with db_session() as repo:
        return _public(repo, repo.get_profile())


@router.put("", response_model=ProfilePublic)
def update_profile(req: ProfileUpdate) -> ProfilePublic:
    """Save name and servicenow.com email (changing the email resets its approval)."""
    with db_session() as repo:
        return _public(repo, repo.update_profile_identity(req.display_name, req.email, _now()))


@router.put("/avatar/preset", response_model=ProfilePublic)
def choose_preset_avatar(req: PresetRequest) -> ProfilePublic:
    """Use one of the built-in avatars."""
    if req.preset not in PRESET_AVATARS:
        raise HTTPException(status_code=422, detail="Unknown avatar.")
    delete_avatar()
    with db_session() as repo:
        return _public(repo, repo.set_profile_avatar("preset", req.preset, _now()))


@router.put("/avatar", response_model=ProfilePublic)
async def upload_avatar(request: Request) -> ProfilePublic:
    """Upload a PNG, JPEG or WebP picture as the raw request body (max 2 MB)."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=413, detail="Picture is larger than 2 MB.")
    data = await request.body()
    if len(data) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=413, detail="Picture is larger than 2 MB.")
    content_type = sniff_image(data)
    if content_type is None:
        raise HTTPException(status_code=415, detail="Use a PNG, JPEG or WebP picture.")
    save_avatar(data, content_type)
    with db_session() as repo:
        return _public(repo, repo.set_profile_avatar("upload", None, _now()))


@router.delete("/avatar", response_model=ProfilePublic)
def remove_avatar() -> ProfilePublic:
    """Remove the avatar (initials are shown instead)."""
    delete_avatar()
    with db_session() as repo:
        return _public(repo, repo.set_profile_avatar("none", None, _now()))


@router.get("/avatar")
def get_avatar() -> Response:
    """Serve the uploaded picture."""
    found = load_avatar()
    if found is None:
        raise HTTPException(status_code=404, detail="No uploaded avatar.")
    data, content_type = found
    return Response(
        content=data,
        media_type=content_type,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-cache"},
    )


@router.post("/verification/send")
def send_verification_code(factory: MailerFactory = Depends(mailer_factory)) -> dict[str, Any]:
    """Email a one-time code to the profile's servicenow.com address."""
    with db_session() as repo:
        try:
            sent_to = send_code(repo, factory(repo))
        except NoEmailError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except MailNotConfiguredError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except CooldownError as exc:
            raise HTTPException(
                status_code=429, detail=str(exc), headers={"Retry-After": str(exc.retry_after)}
            ) from exc
        except MailError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"sent_to": sent_to, "expires_in_seconds": int(CODE_TTL.total_seconds())}


@router.post("/verification/confirm", response_model=ProfilePublic)
def confirm_verification_code(req: CodeConfirm) -> ProfilePublic:
    """Approve the profile with the code from the email."""
    with db_session() as repo:
        try:
            confirm_code(repo, req.code)
        except NoPendingCodeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except CodeExpiredError as exc:
            raise HTTPException(status_code=410, detail=str(exc)) from exc
        except TooManyAttemptsError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except WrongCodeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except VerificationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _public(repo, repo.get_profile())


@router.get("/mail", response_model=MailSettingsPublic)
def get_mail_settings() -> MailSettingsPublic:
    """Return the SMTP settings without the password."""
    with db_session() as repo:
        settings = repo.get_mail_settings()
        return MailSettingsPublic(
            **settings.model_dump(), has_password=bool(repo.get_secret(SMTP_PASSWORD_SECRET))
        )


@router.put("/mail", response_model=MailSettingsPublic)
def put_mail_settings(req: MailSettingsUpdate) -> MailSettingsPublic:
    """Save SMTP settings; the password is sealed in the encrypted store."""
    with db_session() as repo:
        settings = repo.put_mail_settings(req)
        return MailSettingsPublic(
            **settings.model_dump(), has_password=bool(repo.get_secret(SMTP_PASSWORD_SECRET))
        )
