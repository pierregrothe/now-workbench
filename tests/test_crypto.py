# tests/test_crypto.py
# Tests for AES-256-GCM secret sealing and master key resolution (ADR-012).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for now_workbench.config.crypto."""

import base64
import os
import stat
from pathlib import Path

import pytest

from now_workbench.platform.config.crypto import (
    SecretDecryptionError,
    mask_api_key,
    resolve_key_file,
    seal_secret,
    unseal_secret,
)


def test_seal_secret_roundtrip_hides_plaintext() -> None:
    """Sealed bytes never contain the plaintext and unseal back exactly."""
    blob = seal_secret("sk-ant-test-supersecret9999", "secret:anthropic_api_key")
    assert b"supersecret9999" not in blob
    assert unseal_secret(blob, "secret:anthropic_api_key") == "sk-ant-test-supersecret9999"


def test_seal_secret_uses_fresh_nonce_per_call() -> None:
    """Two seals of the same plaintext differ (random 96-bit nonce)."""
    assert seal_secret("same", "ctx") != seal_secret("same", "ctx")


def test_unseal_secret_with_wrong_context_raises() -> None:
    """A blob moved to another row or slot fails GCM authentication."""
    blob = seal_secret("pwd", "instance:a")
    with pytest.raises(SecretDecryptionError, match="authentication"):
        unseal_secret(blob, "instance:b")


def test_unseal_secret_tampered_ciphertext_raises() -> None:
    """Flipping one ciphertext bit is detected."""
    blob = bytearray(seal_secret("pwd", "ctx"))
    blob[-1] ^= 0x01
    with pytest.raises(SecretDecryptionError):
        unseal_secret(bytes(blob), "ctx")


def test_unseal_secret_unknown_format_raises() -> None:
    """Blobs without the v1 header are rejected before decryption."""
    with pytest.raises(SecretDecryptionError, match="format"):
        unseal_secret(b"\x09" + b"0" * 40, "ctx")
    with pytest.raises(SecretDecryptionError, match="format"):
        unseal_secret(b"\x01short", "ctx")


def test_unseal_secret_with_different_master_key_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Losing or swapping the master key makes stored secrets unreadable."""
    blob = seal_secret("pwd", "ctx")
    monkeypatch.setenv("WORKBENCH_KEY_FILE", str(tmp_path / "other.key"))
    with pytest.raises(SecretDecryptionError):
        unseal_secret(blob, "ctx")


def test_resolve_key_file_creates_owner_only_key_and_reuses_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The key file is created 0600 on first seal and reused afterwards."""
    key_file = tmp_path / "cfg" / "master.key"
    monkeypatch.setenv("WORKBENCH_KEY_FILE", str(key_file))
    blob = seal_secret("pwd", "ctx")
    assert stat.S_IMODE(key_file.stat().st_mode) == 0o600
    assert len(base64.urlsafe_b64decode(key_file.read_text().strip())) == 32
    assert unseal_secret(blob, "ctx") == "pwd"


def test_resolve_key_file_defaults_to_xdg_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without WORKBENCH_KEY_FILE the key lives under XDG_CONFIG_HOME, not the data dir."""
    monkeypatch.delenv("WORKBENCH_KEY_FILE")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert resolve_key_file() == tmp_path.resolve() / "now-workbench" / "master.key"


def test_seal_secret_with_env_master_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """WORKBENCH_MASTER_KEY takes precedence over any key file."""
    monkeypatch.setenv("WORKBENCH_MASTER_KEY", base64.urlsafe_b64encode(b"k" * 32).decode())
    blob = seal_secret("env-secret", "ctx")
    assert unseal_secret(blob, "ctx") == "env-secret"


def test_seal_secret_with_invalid_env_master_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """A master key that is not 32 bytes of urlsafe base64 is refused."""
    monkeypatch.setenv("WORKBENCH_MASTER_KEY", base64.urlsafe_b64encode(b"short").decode())
    with pytest.raises(ValueError, match="32 bytes"):
        seal_secret("x", "ctx")
    monkeypatch.setenv("WORKBENCH_MASTER_KEY", "not base64 !!")
    with pytest.raises(ValueError, match="base64"):
        seal_secret("x", "ctx")


def test_seal_secret_key_file_creation_race_uses_winner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If another process creates the key file first, its key is adopted."""
    key_file = tmp_path / "race" / "master.key"
    monkeypatch.setenv("WORKBENCH_KEY_FILE", str(key_file))
    winner = base64.urlsafe_b64encode(b"w" * 32).decode()
    real_open = os.open

    def open_after_competitor(path: str, flags: int, mode: int = 0o777) -> int:
        Path(path).write_text(winner + "\n", encoding="ascii")
        return real_open(path, flags, mode)

    monkeypatch.setattr(os, "open", open_after_competitor)
    blob = seal_secret("pwd", "ctx")
    monkeypatch.setattr(os, "open", real_open)
    assert key_file.read_text().strip() == winner
    assert unseal_secret(blob, "ctx") == "pwd"


def test_mask_api_key_lengths() -> None:
    """Masking never reveals more than prefix and last four characters."""
    assert mask_api_key("") == ""
    assert mask_api_key("abcd") == "****"
    assert mask_api_key("shortkey") == "sh...ey"
    assert mask_api_key("sk-ant-api03-secret1234") == "sk-ant-...1234"


def test_seal_secret_reads_preexisting_key_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An existing key file (e.g. restored from backup) is used as-is."""
    key_file = tmp_path / "restored.key"
    key_file.write_text(base64.urlsafe_b64encode(b"r" * 32).decode() + "\n", encoding="ascii")
    monkeypatch.setenv("WORKBENCH_KEY_FILE", str(key_file))
    monkeypatch.setenv("WORKBENCH_MASTER_KEY", base64.urlsafe_b64encode(b"r" * 32).decode())
    env_blob = seal_secret("same-key", "ctx")
    monkeypatch.delenv("WORKBENCH_MASTER_KEY")
    assert unseal_secret(env_blob, "ctx") == "same-key"
