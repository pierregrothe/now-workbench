# src/now_workbench/auth/guard.py
# Request authentication (ASGI middleware), role dependencies and the startup guard.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Enforcement: every HTTP and WebSocket request is authenticated before any route runs."""

import json
from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, Request
from starlette.types import ASGIApp, Receive, Scope, Send

from now_workbench.auth.access import ACCESS_HEADER, AccessValidator
from now_workbench.auth.models import LOCAL_EMAIL, AuthUser, Role
from now_workbench.auth.roles import roles_for

__all__ = [
    "AccessMiddleware",
    "assert_safe_binding",
    "authenticate",
    "current_user",
    "is_loopback_host",
    "require_role",
]

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
# Headers only Cloudflare adds. Seeing them with Access unconfigured means the server is being
# reached through a tunnel it does not know how to authenticate; refuse rather than trust.
_CLOUDFLARE_HEADERS = ("cf-connecting-ip", "cf-ray")


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


def authenticate(
    headers: dict[str, str], validator: AccessValidator, admin_emails: str, consultant_emails: str
) -> tuple[AuthUser | None, str]:
    """Decide who a request is.

    Args:
        headers: Request headers, lower-cased names.
        validator: Cloudflare Access validator.
        admin_emails: Configured admin addresses.
        consultant_emails: Configured Solution Consultant addresses.

    Returns:
        ``(user, "")`` when allowed, otherwise ``(None, reason)``.
    """
    if validator.configured:
        email = validator.email(headers.get(ACCESS_HEADER, ""))
        if email is None:
            return None, "Sign in through Cloudflare Access."
        roles = roles_for(email, admin_emails, consultant_emails)
        if not roles:
            return None, f"{email} has no role on this workbench."
        return AuthUser(email=email, roles=roles, mode="cloudflare"), ""
    if any(name in headers for name in _CLOUDFLARE_HEADERS) or ACCESS_HEADER in headers:
        return None, "Cloudflare traffic reached a server where Access is not configured."
    return AuthUser(email=LOCAL_EMAIL, roles=frozenset(Role), mode="local"), ""


class AccessMiddleware:
    """Pure ASGI middleware so HTTP and WebSocket requests are both covered."""

    def __init__(
        self,
        app: ASGIApp,
        validator: AccessValidator,
        admin_emails: Callable[[], str],
        consultant_emails: Callable[[], str],
    ) -> None:
        self.app = app
        self.validator = validator
        self._admins = admin_emails
        self._consultants = consultant_emails

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        user, reason = authenticate(headers, self.validator, self._admins(), self._consultants())
        if user is None:
            await self._deny(scope, receive, send, reason)
            return
        scope.setdefault("state", {})["user"] = user
        await self.app(scope, receive, send)

    @staticmethod
    async def _deny(scope: Scope, receive: Receive, send: Send, reason: str) -> None:
        if scope["type"] == "websocket":
            await receive()
            await send({"type": "websocket.close", "code": 1008})
            return
        body = json.dumps({"detail": reason}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 403,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body})


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
