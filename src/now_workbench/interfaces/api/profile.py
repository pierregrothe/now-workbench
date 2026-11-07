# src/now_workbench/interfaces/api/profile.py
# REST routes for the signed-in user's identity, profile and avatar.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Profile API. Identity comes from Cloudflare Access, never from the request body."""

import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from now_workbench.domains.identity import AuthUser
from now_workbench.domains.profile import (
    MAX_AVATAR_BYTES,
    PRESET_AVATARS,
    AvatarPublic,
    PresetRequest,
    ProfilePublic,
    ProfileRecord,
    ProfileRepository,
    ProfileUpdate,
    delete_avatar,
    load_avatar,
    save_avatar,
    sniff_image,
)
from now_workbench.interfaces.api.guard import current_user
from now_workbench.platform.db.session import db_session

__all__ = ["router"]

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _public(user: AuthUser, record: ProfileRecord) -> ProfilePublic:
    url = (
        f"/api/profile/avatar?v={record.avatar_updated_at}"
        if record.avatar_kind == "upload"
        else None
    )
    return ProfilePublic(
        email=user.email,
        display_name=record.display_name,
        roles=sorted(role.value for role in user.roles),
        auth_mode=user.mode,
        avatar=AvatarPublic(kind=record.avatar_kind, preset=record.avatar_preset, url=url),
    )


def _profile(conn: sqlite3.Connection, user: AuthUser) -> ProfileRecord:
    return ProfileRepository(conn).get_profile(user.email)


@router.get("", response_model=ProfilePublic)
def get_profile(user: AuthUser = Depends(current_user)) -> ProfilePublic:
    """Return who is signed in, their roles and their profile."""
    with db_session() as conn:
        return _public(user, _profile(conn, user))


@router.put("", response_model=ProfilePublic)
def update_profile(req: ProfileUpdate, user: AuthUser = Depends(current_user)) -> ProfilePublic:
    """Save the display name."""
    with db_session() as conn:
        return _public(
            user, ProfileRepository(conn).update_profile_name(user.email, req.display_name, _now())
        )


@router.put("/avatar/preset", response_model=ProfilePublic)
def choose_preset_avatar(
    req: PresetRequest, user: AuthUser = Depends(current_user)
) -> ProfilePublic:
    """Use one of the built-in avatars."""
    if req.preset not in PRESET_AVATARS:
        raise HTTPException(status_code=422, detail="Unknown avatar.")
    delete_avatar(user.email)
    with db_session() as conn:
        return _public(
            user,
            ProfileRepository(conn).set_profile_avatar(user.email, "preset", req.preset, _now()),
        )


@router.put("/avatar", response_model=ProfilePublic)
async def upload_avatar(request: Request, user: AuthUser = Depends(current_user)) -> ProfilePublic:
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
    save_avatar(user.email, data, content_type)
    with db_session() as conn:
        return _public(
            user, ProfileRepository(conn).set_profile_avatar(user.email, "upload", None, _now())
        )


@router.delete("/avatar", response_model=ProfilePublic)
def remove_avatar(user: AuthUser = Depends(current_user)) -> ProfilePublic:
    """Remove the avatar (initials are shown instead)."""
    delete_avatar(user.email)
    with db_session() as conn:
        return _public(
            user, ProfileRepository(conn).set_profile_avatar(user.email, "none", None, _now())
        )


@router.get("/avatar")
def get_avatar(user: AuthUser = Depends(current_user)) -> Response:
    """Serve the signed-in user's uploaded picture."""
    found = load_avatar(user.email)
    if found is None:
        raise HTTPException(status_code=404, detail="No uploaded avatar.")
    data, content_type = found
    return Response(
        content=data,
        media_type=content_type,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-cache"},
    )
