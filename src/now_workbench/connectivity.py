"""Live ServiceNow instance connectivity and authentication verification."""

import httpx

from now_workbench.config.settings import settings
from now_workbench.db.models import InstanceRecord
from now_workbench.db.repository import DatabaseRepository
from now_workbench.releases import BUILD_PROPERTY, parse_release_family

__all__ = ["check_and_record_instance", "detect_instance_release", "verify_instance_authentication"]


def verify_instance_authentication(
    inst: InstanceRecord,
    timeout: float = 5.0,
    client: httpx.Client | None = None,
    fake_mode: bool = False,
) -> tuple[str, str, int]:
    """Test instance credentials against the ServiceNow Table API."""
    if _is_simulated(inst, fake_mode):
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


def _is_simulated(inst: InstanceRecord, fake_mode: bool) -> bool:
    """Return True when the instance must not be contacted over the network."""
    return (
        fake_mode
        or getattr(settings, "fake_mode", False)
        or inst.url.startswith("fake://")
        or inst.url.startswith("http://fake")
    )


def detect_instance_release(
    inst: InstanceRecord,
    timeout: float = 5.0,
    client: httpx.Client | None = None,
) -> str | None:
    """Read the instance's ``glide.war`` build property and return its release family.

    Args:
        inst: Instance with decrypted credentials.
        timeout: Request timeout in seconds.
        client: Optional preconfigured HTTP client (closed after use).

    Returns:
        The release family (e.g. ``"Australia"``), or ``None`` when the property is not
        readable with these credentials or the instance cannot be reached.
    """
    url = f"{inst.url.rstrip('/')}/api/now/table/sys_properties"
    params = {"sysparm_query": f"name={BUILD_PROPERTY}", "sysparm_fields": "value"}
    auth = (inst.username, inst.password) if inst.auth_type == "basic" else None
    try:
        http_ctx = client if client is not None else httpx.Client(timeout=timeout)
        with http_ctx as cl:
            res = cl.get(url, params=params, auth=auth, headers={"Accept": "application/json"})
        if res.status_code != 200:
            return None
        rows = res.json().get("result") or []
        return parse_release_family(str(rows[0].get("value", ""))) if rows else None
    except httpx.HTTPError, ValueError:
        return None


def check_and_record_instance(
    repo: DatabaseRepository,
    inst: InstanceRecord,
    timeout: float = 5.0,
    fake_mode: bool = False,
    transport: httpx.BaseTransport | None = None,
) -> tuple[str, str, int]:
    """Verify authentication, detect the release when authenticated, and persist both.

    The single entry point for "test this instance": every caller gets the same
    status semantics and the registry release always reflects the live build.

    Args:
        repo: Repository to record the result in.
        inst: Instance with decrypted credentials.
        timeout: Per-request timeout in seconds.
        fake_mode: Simulate instead of contacting the network.
        transport: Optional HTTP transport (in-memory in tests).

    Returns:
        ``(status, message, http_code)`` from the authentication check.
    """

    def client() -> httpx.Client | None:
        if transport is None:
            return None
        return httpx.Client(transport=transport, timeout=timeout)

    status, message, code = verify_instance_authentication(
        inst, timeout=timeout, client=client(), fake_mode=fake_mode
    )
    release = None
    if status == "authenticated" and not _is_simulated(inst, fake_mode):
        release = detect_instance_release(inst, timeout=timeout, client=client())
    repo.update_instance_status(inst.id, status, release=release)
    return status, message, code
