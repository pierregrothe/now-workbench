# src/now_workbench/domains/profile/__init__.py
# Public root of the profile domain: other packages import only what is listed here.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Profile package."""

from now_workbench.domains.profile.avatars import (
    MAX_AVATAR_BYTES,
    PRESET_AVATARS,
    delete_avatar,
    load_avatar,
    save_avatar,
    sniff_image,
)
from now_workbench.domains.profile.models import (
    AvatarPublic,
    PresetRequest,
    ProfilePublic,
    ProfileRecord,
    ProfileUpdate,
)
from now_workbench.domains.profile.repository import ProfileRepository
from now_workbench.domains.profile.service import choose_preset_avatar, rename

__all__ = [
    "AvatarPublic",
    "choose_preset_avatar",
    "delete_avatar",
    "load_avatar",
    "MAX_AVATAR_BYTES",
    "PRESET_AVATARS",
    "PresetRequest",
    "ProfilePublic",
    "ProfileRecord",
    "ProfileRepository",
    "ProfileUpdate",
    "rename",
    "save_avatar",
    "sniff_image",
]
