# src/now_workbench/domains/instances/__init__.py
# Public root of the instances domain: other packages import only what is listed here.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Instances domain (ADR-015)."""

from now_workbench.domains.instances.bootstrap import seed_default_instance_if_empty
from now_workbench.domains.instances.connectivity import check_and_record_instance
from now_workbench.domains.instances.models import (
    INSTANCE_PURPOSES,
    InstanceCreate,
    InstanceNode,
    InstanceProfile,
    InstancePublic,
    InstancePurpose,
    InstanceRecord,
    InstanceUpdate,
)
from now_workbench.domains.instances.repository import InstanceRepository

__all__ = [
    "check_and_record_instance",
    "INSTANCE_PURPOSES",
    "InstanceCreate",
    "InstanceNode",
    "InstanceProfile",
    "InstancePublic",
    "InstancePurpose",
    "InstanceRecord",
    "InstanceRepository",
    "InstanceUpdate",
    "seed_default_instance_if_empty",
]
