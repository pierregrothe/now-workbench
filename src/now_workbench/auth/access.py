# src/now_workbench/auth/access.py
# Validate the signed token Cloudflare Access attaches to every authenticated request.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Cloudflare Access token validation (same approach as the rivian gateway).

Cloudflare authenticates the person (Apple or Google) before traffic reaches the server and
attaches a JWT signed with a key only Cloudflare holds. Verifying that signature is the one
identity assertion this server can check itself. Verification is delegated to PyJWT: algorithm
confusion and a forgotten claim are the classic traps of this token family.
"""

import logging
import time
from collections.abc import Callable
from typing import Any

import jwt
from jwt import PyJWKClient

__all__ = ["ACCESS_HEADER", "JWKS_CACHE_SECONDS", "AccessValidator", "KeyResolver"]

logger = logging.getLogger(__name__)

ACCESS_HEADER = "cf-access-jwt-assertion"
JWKS_CACHE_SECONDS = 3600.0

type KeyResolver = Callable[[str], Any]


class AccessValidator:
    """Validates ``Cf-Access-Jwt-Assertion`` tokens for one Access application."""

    def __init__(
        self, team_domain: str, audience: str, key_resolver: KeyResolver | None = None
    ) -> None:
        """Prepare the validator.

        Args:
            team_domain: Access team domain, for example ``example.cloudflareaccess.com``.
            audience: The Access application's AUD tag.
            key_resolver: Returns the public key for a token (tests inject a fixed key;
                production fetches Cloudflare's published keys).
        """
        self.team_domain = team_domain.strip().rstrip("/")
        self.audience = audience.strip()
        self._resolver = key_resolver
        self._client: PyJWKClient | None = None
        self._fetched_at = 0.0

    @property
    def configured(self) -> bool:
        """True when both the team domain and the audience are set."""
        return bool(self.team_domain and self.audience)

    @property
    def issuer(self) -> str:
        """The ``iss`` Cloudflare puts in the token."""
        return f"https://{self.team_domain}"

    def _public_key(self, token: str) -> Any:
        if self._resolver is not None:
            return self._resolver(token)
        expired = (time.monotonic() - self._fetched_at) > JWKS_CACHE_SECONDS
        if self._client is None or expired:
            self._client = PyJWKClient(f"{self.issuer}/cdn-cgi/access/certs", cache_keys=True)
            self._fetched_at = time.monotonic()
        return self._client.get_signing_key_from_jwt(token).key

    def email(self, token: str) -> str | None:
        """Return the verified email in the token, or None for any token we cannot trust.

        A token is refused when it is missing, expired, badly signed, for another application,
        from another team, or carries no email (for example a service token).
        """
        if not (self.configured and token):
            return None
        try:
            claims = jwt.decode(
                token,
                self._public_key(token),
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "aud", "iss"]},
            )
        except Exception as err:
            # Broad on purpose: besides PyJWT refusals, fetching the keys can fail on the
            # network. A token we cannot verify is a token we refuse.
            logger.warning("Access token refused: %s", err)
            return None
        email = claims.get("email")
        return email.strip().lower() if isinstance(email, str) and "@" in email else None
