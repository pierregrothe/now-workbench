"""Live ServiceNow instance connectivity and authentication verification."""

import sqlite3

import httpx

from now_workbench.domains.instances.models import InstanceRecord
from now_workbench.domains.instances.profile import collect_instance_profile
from now_workbench.domains.instances.repository import InstanceRepository
from now_workbench.platform.config.settings import settings

__all__ = ["check_and_record_instance", "is_simulated", "verify_instance_authentication"]


def verify_instance_authentication(
    inst: InstanceRecord,
    timeout: float = 5.0,
    client: httpx.Client | None = None,
    fake_mode: bool = False,
) -> tuple[str, str, int]:
    """Test instance credentials against the ServiceNow Table API."""
    if is_simulated(inst, fake_mode):
        if "auth-failed" in inst.url:
            return ("auth_failed", "Authentication failed (HTTP 401)", 401)
        if "unreachable" in inst.url:
            return ("unreachable", "Connection error: Simulated unreachable", 0)
        return ("authenticated", f"Authenticated as '{inst.username}'", 200)

    base_url = inst.url.rstrip("/")
    url = f"{base_url}/api/now/table/incident?sysparm_limit=1"
    auth = (inst.username, inst.password) if inst.auth_type == "basic" else None
    headers = {"Accept": "application/json"}
    try:
        http_ctx = (
            client
            if client is not None
            else httpx.Client(
                timeout=httpx.Timeout(timeout, connect=min(3.0, timeout)),
                follow_redirects=True,
            )
        )
        with http_ctx as cl:
            res = cl.get(url, auth=auth, headers=headers)
            if res.status_code == 200:
                return ("authenticated", f"Authenticated as '{inst.username}'", 200)
            if res.status_code in (401, 403):
                return (
                    "auth_failed",
                    f"Authentication failed (HTTP {res.status_code})",
                    res.status_code,
                )
            return ("error", f"HTTP {res.status_code}", res.status_code)
    except Exception as exc:
        return ("unreachable", f"Connection error: {exc}", 0)


def is_simulated(inst: InstanceRecord, fake_mode: bool) -> bool:
    """Return True when the instance must not be contacted over the network."""
    return (
        fake_mode
        or getattr(settings, "fake_mode", False)
        or inst.url.startswith("fake://")
        or inst.url.startswith("http://fake")
    )


def check_and_record_instance(
    conn: sqlite3.Connection,
    inst: InstanceRecord,
    timeout: float = 5.0,
    fake_mode: bool = False,
    transport: httpx.BaseTransport | None = None,
) -> tuple[str, str, int]:
    """Verify authentication and, when authenticated, refresh the platform profile.

    The single entry point for "test this instance" (ADR-014): every caller gets the
    same status semantics, and the stored release, environment, datacenter and node
    facts always come from the live instance -- never from user input.

    Args:
        conn: Open database connection to record the result in.
        inst: Instance with decrypted credentials.
        timeout: Per-request timeout in seconds.
        fake_mode: Simulate instead of contacting the network.
        transport: Optional HTTP transport (in-memory in tests).

    Returns:
        ``(status, message, http_code)`` from the authentication check.
    """

    instance_repo = InstanceRepository(conn)

    def client() -> httpx.Client | None:
        if transport is None:
            return None
        return httpx.Client(transport=transport, timeout=timeout)

    status, message, code = verify_instance_authentication(
        inst, timeout=timeout, client=client(), fake_mode=fake_mode
    )
    instance_repo.update_instance_status(inst.id, status)
    if status == "authenticated" and not is_simulated(inst, fake_mode):
        profile = collect_instance_profile(inst, client=client(), timeout=timeout)
        if profile is not None:
            instance_repo.save_instance_profile(profile)
    return status, message, code
