"""Per-domain repositories over one shared SQLite connection (ADR-015)."""

from now_workbench.db.repos.artifacts import ArtifactRepository
from now_workbench.db.repos.base import Repository
from now_workbench.db.repos.chat import ChatRepository
from now_workbench.db.repos.groups import GroupRepository
from now_workbench.db.repos.instances import InstanceRepository, row_to_instance
from now_workbench.db.repos.preferences import PreferencesRepository
from now_workbench.db.repos.profile import ProfileRepository
from now_workbench.db.repos.seeds import SeedRepository
from now_workbench.db.repos.templates import TemplateRepository
from now_workbench.db.repos.threads import ThreadRepository
from now_workbench.db.repos.users import UserRepository

__all__ = [
    "ArtifactRepository",
    "ChatRepository",
    "GroupRepository",
    "InstanceRepository",
    "PreferencesRepository",
    "ProfileRepository",
    "SeedRepository",
    "TemplateRepository",
    "ThreadRepository",
    "UserRepository",
    "Repository",
    "row_to_instance",
]
