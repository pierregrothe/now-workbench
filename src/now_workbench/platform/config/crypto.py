"""AES-256-GCM encryption at rest for workbench secrets (ADR-012).

Secrets (instance credentials, the Claude API key) are sealed with AES-256-GCM
under a 256-bit master key that lives OUTSIDE the data directory, so a copy of
``workbench.db`` alone never yields plaintext. Every ciphertext is bound to a
context string (passed as GCM associated data), so a sealed blob cannot be
moved to another row or secret slot without failing authentication.

Master key resolution order:
  1. ``WORKBENCH_MASTER_KEY`` -- urlsafe base64 of exactly 32 bytes.
  2. ``WORKBENCH_KEY_FILE`` -- path to a key file (created on first use).
  3. ``$XDG_CONFIG_HOME/now-workbench/master.key`` (default ``~/.config``).
"""

import base64
import os
import secrets
from functools import lru_cache
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

__all__ = [
    "SecretDecryptionError",
    "mask_api_key",
    "resolve_key_file",
    "seal_secret",
    "unseal_secret",
]

_FORMAT_VERSION = b"\x01"
_NONCE_LEN = 12
_KEY_LEN = 32


class SecretDecryptionError(ValueError):
    """Raised when a sealed secret cannot be authenticated or decrypted."""


def resolve_key_file() -> Path:
    """Return the master key file path from the environment or XDG defaults.

    Returns:
        Absolute path of the key file (it may not exist yet).
    """
    explicit = os.environ.get("WORKBENCH_KEY_FILE")
    if explicit:
        return Path(explicit).expanduser().resolve()
    config_home = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(config_home).expanduser().resolve() / "now-workbench" / "master.key"


def _decode_key(encoded: str, source: str) -> bytes:
    """Decode a urlsafe base64 master key and enforce its 256-bit length."""
    try:
        key = base64.urlsafe_b64decode(encoded.strip().encode("ascii"))
    except ValueError as exc:
        raise ValueError(f"{source} is not valid urlsafe base64.") from exc
    if len(key) != _KEY_LEN:
        raise ValueError(f"{source} must decode to exactly {_KEY_LEN} bytes.")
    return key


def _read_or_create_key_file(path: Path) -> bytes:
    """Load the key file, creating it with owner-only permissions on first use."""
    if path.exists():
        return _decode_key(path.read_text(encoding="ascii"), str(path))
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    encoded = base64.urlsafe_b64encode(secrets.token_bytes(_KEY_LEN)).decode("ascii")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        # Lost a creation race with another process: use the winner's key.
        return _decode_key(path.read_text(encoding="ascii"), str(path))
    with os.fdopen(fd, "w", encoding="ascii") as handle:
        handle.write(encoded + "\n")
    return _decode_key(encoded, str(path))


@lru_cache(maxsize=8)
def _cipher_for(env_key: str, key_path: str) -> AESGCM:
    """Build (and cache per key source) the AES-GCM cipher."""
    if env_key:
        return AESGCM(_decode_key(env_key, "WORKBENCH_MASTER_KEY"))
    return AESGCM(_read_or_create_key_file(Path(key_path)))


def _cipher() -> AESGCM:
    """Return the AES-GCM cipher for the currently configured master key."""
    return _cipher_for(os.environ.get("WORKBENCH_MASTER_KEY", ""), str(resolve_key_file()))


def seal_secret(plaintext: str, context: str) -> bytes:
    """Encrypt a secret with AES-256-GCM, bound to a context string.

    Args:
        plaintext: Secret value to encrypt.
        context: Binding label (e.g. ``instance:<id>``); required again to unseal.

    Returns:
        ``version || nonce || ciphertext+tag`` as raw bytes for a BLOB column.
    """
    nonce = secrets.token_bytes(_NONCE_LEN)
    sealed = _cipher().encrypt(nonce, plaintext.encode("utf-8"), context.encode("utf-8"))
    return _FORMAT_VERSION + nonce + sealed


def unseal_secret(blob: bytes, context: str) -> str:
    """Decrypt and authenticate a blob produced by ``seal_secret``.

    Args:
        blob: Sealed bytes read from the database.
        context: The binding label used when sealing.

    Returns:
        The decrypted plaintext.

    Raises:
        SecretDecryptionError: Unknown format, wrong master key, wrong context,
            or tampered ciphertext.
    """
    if blob[:1] != _FORMAT_VERSION or len(blob) <= 1 + _NONCE_LEN:
        raise SecretDecryptionError("Unsupported sealed secret format.")
    nonce = blob[1 : 1 + _NONCE_LEN]
    try:
        plain = _cipher().decrypt(nonce, blob[1 + _NONCE_LEN :], context.encode("utf-8"))
    except InvalidTag as exc:
        raise SecretDecryptionError(
            "Secret failed authentication: wrong master key or tampered data."
        ) from exc
    return plain.decode("utf-8")


def mask_api_key(plaintext: str) -> str:
    """Return a non-sensitive masked preview of an API key for UI/CLI display."""
    clean = plaintext.strip()
    if not clean:
        return ""
    if len(clean) <= 4:
        return "****"
    if len(clean) <= 10:
        return f"{clean[:2]}...{clean[-2:]}"
    return f"{clean[:7]}...{clean[-4:]}"
