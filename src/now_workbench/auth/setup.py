# src/now_workbench/auth/setup.py
# First-run setup code: proves the person claiming the first admin seat can read the server log.
# Author: Pierre Grothe
# Date: 2026-11-06
"""One-time setup code for the first administrator (ADR-017).

The code lives only in memory (hashed) and in the server log. Reading it needs access to the
server, which a visitor who merely reaches the web page does not have; that is what makes it
safer than a first-come password form. Five wrong tries replace it with a new code.
"""

import hashlib
import hmac
import secrets
import threading
from collections.abc import Callable

__all__ = [
    "CODE_ALPHABET",
    "MAX_ATTEMPTS",
    "SetupCodes",
    "SetupError",
    "TooManyAttemptsError",
    "WrongCodeError",
]

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 8
MAX_ATTEMPTS = 5


class SetupError(Exception):
    """Base class for setup-code failures."""


class WrongCodeError(SetupError):
    """The code does not match."""

    def __init__(self, remaining: int) -> None:
        super().__init__(f"That setup code is not correct. {remaining} attempt(s) left.")
        self.remaining = remaining


class TooManyAttemptsError(SetupError):
    """Too many wrong codes: a new code was written to the server log."""


def _normalize(raw: str) -> str:
    return "".join(ch for ch in raw.upper() if ch not in " -\t")


def _digest(code: str, salt: bytes) -> bytes:
    return hashlib.sha256(salt + code.encode()).digest()


class SetupCodes:
    """Holds the current setup code (hash only) and announces new ones."""

    def __init__(self, announce: Callable[[str], None]) -> None:
        """Create an empty holder.

        Args:
            announce: Called with the readable code whenever a new one is issued (the log).
        """
        self._announce = announce
        self._lock = threading.Lock()
        self._salt = b""
        self._hash = b""
        self._attempts = 0

    @property
    def active(self) -> bool:
        """True while a code is waiting to be used."""
        return bool(self._hash)

    def issue(self) -> None:
        """Replace any code with a new one and announce it."""
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(_CODE_LENGTH))
        with self._lock:
            self._salt = secrets.token_bytes(16)
            self._hash = _digest(code, self._salt)
            self._attempts = 0
        self._announce(f"{code[:4]}-{code[4:]}")

    def clear(self) -> None:
        """Forget the code (setup is complete)."""
        with self._lock:
            self._salt = b""
            self._hash = b""
            self._attempts = 0

    def redeem(self, entered: str) -> None:
        """Accept the code once.

        Raises:
            SetupError: No code is active.
            WrongCodeError: The code does not match.
            TooManyAttemptsError: Fifth miss; a new code was issued.
        """
        with self._lock:
            if not self._hash:
                raise SetupError("No setup code is active.")
            if hmac.compare_digest(_digest(_normalize(entered), self._salt), self._hash):
                self._salt = b""
                self._hash = b""
                self._attempts = 0
                return
            self._attempts += 1
            remaining = MAX_ATTEMPTS - self._attempts
        if remaining <= 0:
            self.issue()
            raise TooManyAttemptsError(
                "Too many wrong codes. A new setup code was written to the server log."
            )
        raise WrongCodeError(remaining)
