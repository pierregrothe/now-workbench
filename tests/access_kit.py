# tests/access_kit.py
# Shared helpers for tests that sign in through a test Cloudflare Access validator.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Signed Access headers and an Access-protected app for multi-user tests (ADR-016/018)."""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from now_workbench.api.app import create_app
from now_workbench.auth.access import ACCESS_HEADER, AccessValidator
from now_workbench.auth.models import Role
from now_workbench.db import db_session
from now_workbench.db.repos.users import UserRepository

__all__ = ["as_user", "multi_user_client"]

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_TEAM, _AUD = "kit.cloudflareaccess.com", "kit-aud"


def as_user(email: str) -> dict[str, str]:
    """Return headers carrying a valid Access token for ``email``."""
    now = int(time.time())
    claims: dict[str, Any] = {
        "aud": _AUD,
        "iss": f"https://{_TEAM}",
        "iat": now,
        "exp": now + 600,
        "email": email,
    }
    return {ACCESS_HEADER: jwt.encode(claims, _KEY, algorithm="RS256")}


@contextmanager
def multi_user_client(admin: str, consultants: tuple[str, ...]) -> Iterator[TestClient]:
    """Yield an Access-protected app where ``admin`` is set up and ``consultants`` are members.

    Args:
        admin: The administrator (also a consultant).
        consultants: Further members holding only the Solution Consultant role.

    Yields:
        A started test client.
    """
    with db_session() as conn:
        user_repo = UserRepository(conn)
        user_repo.put_user(admin, frozenset(Role), added_by="test")
        for email in consultants:
            user_repo.put_user(email, frozenset({Role.SOLUTION_CONSULTANT}), added_by="test")
    validator = AccessValidator(_TEAM, _AUD, key_resolver=lambda _t: _KEY.public_key())
    with TestClient(create_app(access_validator=validator)) as client:
        yield client
