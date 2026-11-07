# src/now_workbench/interfaces/api/guard.py
# Request authentication (ASGI middleware), role dependencies and the startup guard.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Enforcement: every HTTP and WebSocket request is authenticated before any route runs."""

import json
from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, Request
from starlette.types import ASGIApp, Receive, Scope, Send

from now_workbench.domains.identity import AuthUser, Role
from now_workbench.interfaces.api.access import ACCESS_HEADER, AccessValidator
from now_workbench.platform.owner import LOCAL_EMAIL, owner_scope

__all__ = [
    "HEALTH_PATH",
    "AccessMiddleware",
    "Decision",
    "assert_safe_binding",
    "authenticate",
    "current_user",
    "is_loopback_host",
    "require_role",
]

HEALTH_PATH = "/healthz"
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
# Headers only Cloudflare adds. Seeing them with Access unconfigured means the server is being
# reached through a tunnel it does not know how to authenticate; refuse rather than trust.
_CLOUDFLARE_HEADERS = ("cf-connecting-ip", "cf-ray")
# In local mode no proxy is trusted, so a forwarding header can only mean an unknown proxy in
# front (or a forged header). Refusing makes that setup fail loudly instead of opening silently.
_FORWARDING_HEADERS = ("x-forwarded-for", "forwarded", "x-real-ip")
# Paths a signed-in person without a role may still use: the UI itself and first-run setup.
_SETUP_API = ("/api/setup",)
_API_PREFIXES = ("/api/", "/ws/", "/docs", "/redoc", "/openapi.json")

type Decision = tuple[AuthUser | None, str, str]


def is_loopback_host(host: str) -> bool:
    """True when binding ``host`` exposes the server to this machine only."""
    return host.strip().lower() in _LOOPBACK


def assert_safe_binding(host: str, validator: AccessValidator) -> None:
    """Refuse to listen beyond loopback unless Cloudflare Access is configured.

    Raises:
        RuntimeError: ``host`` is reachable from other machines and Access is not configured.
    """
    if not is_loopback_host(host) and not validator.configured:
        raise RuntimeError(
            f"Refusing to listen on {host}: the API holds credentials and has no sign-in. "
            "Set WORKBENCH_ACCESS_TEAM_DOMAIN and WORKBENCH_ACCESS_AUDIENCE (Cloudflare Access), "
            "or bind to 127.0.0.1."
        )


def _roleless_may_use(path: str) -> bool:
    if path == "/api/setup" or path.startswith(_SETUP_API[0] + "/"):
        return True
    return not path.startswith(_API_PREFIXES)


def authenticate(
    headers: dict[str, str],
    path: str,
    validator: AccessValidator,
    lookup_roles: Callable[[str], frozenset[Role]],
    setup_pending: Callable[[], bool],
) -> Decision:
    """Decide who a request is and whether it may proceed.

    Args:
        headers: Request headers, lower-cased names.
        path: Request path.
        validator: Cloudflare Access validator.
        lookup_roles: Returns the stored roles of an email.
        setup_pending: True while no administrator exists yet.

    Returns:
        ``(user, "", "")`` when allowed, otherwise ``(None, reason, code)`` where ``code`` is
        ``signin``, ``setup_required`` or ``no_role``.
    """
    if validator.configured:
        email = validator.email(headers.get(ACCESS_HEADER, ""))
        if email is None:
            return None, "Sign in through Cloudflare Access.", "signin"
        user = AuthUser(email=email, roles=lookup_roles(email), mode="cloudflare")
        if user.roles or _roleless_may_use(path):
            return user, "", ""
        if setup_pending():
            return None, "This workbench is not set up yet.", "setup_required"
        return None, f"{email} has no role on this workbench.", "no_role"
    if any(name in headers for name in _CLOUDFLARE_HEADERS) or ACCESS_HEADER in headers:
        return None, "Cloudflare traffic reached a server where Access is not configured.", "signin"
    if any(name in headers for name in _FORWARDING_HEADERS):
        return None, "Requests through a proxy need Cloudflare Access configured.", "signin"
    return AuthUser(email=LOCAL_EMAIL, roles=frozenset(Role), mode="local"), "", ""


class AccessMiddleware:
    """Pure ASGI middleware so HTTP and WebSocket requests are both covered."""

    def __init__(
        self,
        app: ASGIApp,
        validator: AccessValidator,
        lookup_roles: Callable[[str], frozenset[Role]],
        setup_pending: Callable[[], bool],
        act_as: Callable[[AuthUser], AuthUser] | None = None,
    ) -> None:
        self.app = app
        self.validator = validator
        self._lookup = lookup_roles
        self._pending = setup_pending
        self._act_as = act_as

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        if scope["type"] == "http" and scope["path"] == HEALTH_PATH:
            await self._json(send, 200, {"status": "ok"})
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        user, reason, code = authenticate(
            headers, scope["path"], self.validator, self._lookup, self._pending
        )
        if user is None:
            if scope["type"] == "websocket":
                await receive()
                await send({"type": "websocket.close", "code": 1008})
                return
            await self._json(send, 403, {"detail": reason, "code": code})
            return
        if self._act_as is not None and user.roles:
            # Impersonation (ADR-020): from here on the request is the impersonated person.
            user = self._act_as(user)
        scope.setdefault("state", {})["user"] = user
        with owner_scope(user.email):
            await self.app(scope, receive, send)

    @staticmethod
    async def _json(send: Send, status: int, payload: dict[str, str]) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": json.dumps(payload).encode()})


def current_user(request: Request) -> AuthUser:
    """FastAPI dependency: the authenticated user set by the middleware."""
    user: Any = request.scope.get("state", {}).get("user")
    if not isinstance(user, AuthUser):
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return user


def require_role(role: Role) -> Callable[..., AuthUser]:
    """Build a dependency that allows only users holding ``role``."""

    def dependency(user: AuthUser = Depends(current_user)) -> AuthUser:
        if role not in user.roles:
            raise HTTPException(status_code=403, detail=f"This needs the {role.value} role.")
        return user

    return dependency
