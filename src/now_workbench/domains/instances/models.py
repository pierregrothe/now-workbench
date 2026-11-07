# src/now_workbench/domains/instances/models.py
# Instance registry models: records, credentials input, detected profile and nodes.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Instance models."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from now_workbench.domains.releases import UNKNOWN_RELEASE

__all__ = [
    "INSTANCE_PURPOSES",
    "InstanceCreate",
    "InstanceNode",
    "InstanceProfile",
    "InstancePublic",
    "InstancePurpose",
    "InstanceRecord",
    "InstanceUpdate",
]

# What the owner uses the instance for. Declared, never detected: ServiceNow reports how an
# instance was provisioned (a standalone demo reports "prod"), not what it is for.
InstancePurpose = Literal["demo", "development", "test", "production"]


INSTANCE_PURPOSES: tuple[InstancePurpose, ...] = ("demo", "development", "test", "production")


class InstanceNode(BaseModel):
    """One application node of an instance, as reported by sys_cluster_state (ADR-014)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_id: str
    hostname: str
    datacenter: str | None = None
    status: str
    cpu_count: int | None = None
    memory_max_mb: float | None = None
    memory_in_use_mb: float | None = None
    memory_pressure: str | None = None
    started_at: datetime | None = None


class InstanceProfile(BaseModel):
    """Platform facts read from the instance at connection time (ADR-014).

    Every field is optional: what can be read depends on the account's roles
    (``sys_properties`` vs. the admin-only cluster tables).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    instance_id: str
    release: str | None = None
    build_tag: str | None = None
    build_date: str | None = None
    platform_name: str | None = None
    installation_name: str | None = None
    # Platform-reported provisioning facts -- NOT the owner's intent (see InstancePurpose).
    instance_type: str | None = None
    production_property: bool | None = None
    datacenter: str | None = None
    db_product: str | None = None
    db_version: str | None = None
    java_version: str | None = None
    os: str | None = None
    nodes: list[InstanceNode] = Field(default_factory=list)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class InstanceRecord(BaseModel):
    """Registered ServiceNow instance with decrypted credentials (backend use only).

    Never return this model from an API route: use ``InstancePublic`` (ADR-012).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    url: str
    username: str = "admin"
    password: str = ""
    auth_type: str = "basic"
    release: str = UNKNOWN_RELEASE  # read-only: from the detected profile (ADR-014)
    purpose: InstancePurpose = "demo"
    is_default: bool = False
    status: str = "unknown"
    last_checked: datetime | None = None

    def to_public(self, profile: InstanceProfile | None = None) -> InstancePublic:
        """Return the API-safe view of this instance (password withheld)."""
        return InstancePublic(
            id=self.id,
            name=self.name,
            url=self.url,
            username=self.username,
            has_password=bool(self.password),
            auth_type=self.auth_type,
            release=self.release,
            purpose=self.purpose,
            is_default=self.is_default,
            status=self.status,
            last_checked=self.last_checked,
            profile=profile,
        )


class InstancePublic(BaseModel):
    """API-safe view of a registered instance: the password never leaves the backend."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    url: str
    username: str
    has_password: bool
    auth_type: str
    release: str
    purpose: InstancePurpose
    is_default: bool
    status: str
    last_checked: datetime | None = None
    profile: InstanceProfile | None = None


class InstanceCreate(BaseModel):
    """Payload to register a new ServiceNow instance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str | None = None
    name: str
    url: str
    username: str = "admin"
    password: str = ""
    auth_type: str = "basic"
    purpose: InstancePurpose = "demo"
    is_default: bool = False


class InstanceUpdate(BaseModel):
    """Payload to update an existing ServiceNow instance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str | None = None
    url: str | None = None
    username: str | None = None
    password: str | None = None
    auth_type: str | None = None
    purpose: InstancePurpose | None = None
    is_default: bool | None = None
