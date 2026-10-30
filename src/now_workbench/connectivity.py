"""Live ServiceNow instance connectivity and authentication verification."""

import httpx

from now_workbench.config.settings import settings
from now_workbench.db.models import InstanceRecord


def verify_instance_authentication(
    inst: InstanceRecord,
    timeout: float = 5.0,
    client: httpx.Client | None = None,
    fake_mode: bool = False,
) -> tuple[str, str, int]:
    """Test instance credentials against the ServiceNow Table API."""
    if (
        fake_mode
        or getattr(settings, "fake_mode", False)
        or inst.url.startswith("fake://")
        or inst.url.startswith("http://fake")
    ):
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
