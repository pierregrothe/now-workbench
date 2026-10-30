"""Authenticated encryption at rest and key masking for sensitive workbench secrets."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from pathlib import Path

_PREFIX = "enc:v1:"
_SALT_LEN = 16
_NONCE_LEN = 16
_TAG_LEN = 32


def _get_master_secret() -> bytes:
    """Resolve or generate the local master key used to encrypt SQLite secrets."""
    env_key = os.environ.get("WORKBENCH_MASTER_KEY")
    if env_key:
        return env_key.encode("utf-8")

    from now_workbench.config.settings import settings

    env_data = os.environ.get("WORKBENCH_DATA_DIR")
    data_dir = Path(env_data).resolve() if env_data else settings.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    key_file = data_dir / ".workbench_master.key"
    if key_file.exists():
        return key_file.read_bytes()

    generated = secrets.token_hex(32).encode("ascii")
    key_file.write_bytes(generated)
    key_file.chmod(0o600)
    return generated


def _derive_subkeys(master: bytes, salt: bytes) -> tuple[bytes, bytes]:
    """Derive 32-byte encryption key and 32-byte MAC key via PBKDF2-HMAC-SHA256."""
    derived = hashlib.pbkdf2_hmac("sha256", master, salt, 100_000, dklen=64)
    return derived[:32], derived[32:]


def _xor_keystream(enc_key: bytes, nonce: bytes, data: bytes) -> bytes:
    """XOR data with an HMAC-SHA256 counter-mode keystream."""
    out = bytearray(len(data))
    block_count = (len(data) + 31) // 32
    for counter in range(block_count):
        block = hmac.new(enc_key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        start = counter * 32
        end = min(start + 32, len(data))
        for idx in range(start, end):
            out[idx] = data[idx] ^ block[idx - start]
    return bytes(out)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a sensitive string into an authenticated 'enc:v1:...' ciphertext."""
    if not plaintext:
        return ""
    if plaintext.startswith(_PREFIX):
        return plaintext

    master = _get_master_secret()
    salt = secrets.token_bytes(_SALT_LEN)
    nonce = secrets.token_bytes(_NONCE_LEN)
    enc_key, mac_key = _derive_subkeys(master, salt)

    ciphertext = _xor_keystream(enc_key, nonce, plaintext.encode("utf-8"))
    tag = hmac.new(mac_key, salt + nonce + ciphertext, hashlib.sha256).digest()
    blob = base64.urlsafe_b64encode(salt + nonce + tag + ciphertext).decode("ascii")
    return f"{_PREFIX}{blob}"


def decrypt_secret(token: str) -> str:
    """Decrypt and authenticate an 'enc:v1:...' ciphertext back to plaintext."""
    if not token:
        return ""
    if not token.startswith(_PREFIX):
        return token

    raw = base64.urlsafe_b64decode(token[len(_PREFIX) :].encode("ascii"))
    salt = raw[:_SALT_LEN]
    nonce = raw[_SALT_LEN : _SALT_LEN + _NONCE_LEN]
    tag = raw[_SALT_LEN + _NONCE_LEN : _SALT_LEN + _NONCE_LEN + _TAG_LEN]
    ciphertext = raw[_SALT_LEN + _NONCE_LEN + _TAG_LEN :]

    master = _get_master_secret()
    enc_key, mac_key = _derive_subkeys(master, salt)
    expected_tag = hmac.new(mac_key, salt + nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected_tag):
        raise ValueError("Encrypted secret failed authentication check.")

    plaintext_bytes = _xor_keystream(enc_key, nonce, ciphertext)
    return plaintext_bytes.decode("utf-8")


def mask_api_key(plaintext: str) -> str:
    """Return a non-sensitive masked preview of an API key for UI/CLI validation."""
    clean = plaintext.strip()
    if not clean:
        return ""
    if len(clean) <= 4:
        return "****"
    if len(clean) <= 10:
        return f"{clean[:2]}...{clean[-2:]}"
    return f"{clean[:7]}...{clean[-4:]}"
