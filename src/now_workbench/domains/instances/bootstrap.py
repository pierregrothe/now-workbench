# src/now_workbench/domains/instances/bootstrap.py
# Seeds the instance configured in settings when a new database has none.
# Author: Pierre Grothe
# Date: 2026-11-07
"""First-run instance seeding, run by the platform after a migration (ADR-015)."""

import sqlite3

from now_workbench.domains.identity import UserRepository
from now_workbench.domains.instances.models import InstanceCreate
from now_workbench.domains.instances.repository import InstanceRepository
from now_workbench.platform.config.settings import settings
from now_workbench.platform.owner import owner_scope

__all__ = ["seed_default_instance_if_empty"]


def seed_default_instance_if_empty(conn: sqlite3.Connection) -> None:
    """Seed the initial instance from settings when the registry is empty."""
    if not settings.sn_instance_url:
        return
    # Owned by the first administrator, or orphaned until one exists (ADR-018).
    instance_repo = InstanceRepository(conn)
    with owner_scope(UserRepository(conn).first_admin_email()):
        if instance_repo.list_instances():
            return
        instance_repo.add_instance(
            InstanceCreate(
                id="primary-instance",
                name="Primary Instance",
                url=settings.sn_instance_url,
                username=settings.sn_username or "admin",
                password=settings.sn_password,
                auth_type="basic",
                is_default=True,
            )
        )
