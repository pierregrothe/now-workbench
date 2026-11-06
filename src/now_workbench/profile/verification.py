# src/now_workbench/profile/verification.py
# One-time email code generation, hashing and matching for profile approval.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Pure helpers for the email verification code (no I/O)."""

import hashlib
import hmac
import secrets
from datetime import timedelta

__all__ = [
    "CODE_ALPHABET",
    "CODE_LENGTH",
    "CODE_TTL",
    "MAX_ATTEMPTS",
    "RESEND_COOLDOWN",
    "code_matches",
    "format_code",
    "hash_code",
    "new_code",
    "new_salt",
    "normalize_code",
]

# No 0/O/1/I so a code read from an email is hard to mistype.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 8
CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5
RESEND_COOLDOWN = timedelta(seconds=60)


def new_code() -> str:
    """Return a random code (about 40 bits) drawn from the unambiguous alphabet."""
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def new_salt() -> str:
    """Return a random per-code salt."""
    return secrets.token_hex(16)


def format_code(code: str) -> str:
    """Return the code grouped for reading, for example ``ABCD-EFGH``."""
    half = len(code) // 2
    return f"{code[:half]}-{code[half:]}"


def normalize_code(raw: str) -> str:
    """Uppercase the entered code and drop spaces and dashes."""
    return "".join(ch for ch in raw.upper() if ch not in " -\t")


def hash_code(code: str, salt: str) -> str:
    """Return the salted SHA-256 of a normalized code."""
    return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()


def code_matches(entered: str, stored_hash: str, salt: str) -> bool:
    """Compare an entered code with the stored hash in constant time."""
    return hmac.compare_digest(hash_code(normalize_code(entered), salt), stored_hash)
