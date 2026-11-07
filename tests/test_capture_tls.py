# tests/test_capture_tls.py
# Capture and playbook drivers verify instance TLS certificates and say so when they refuse one.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Tests for STORY-057: no certificate bypass anywhere, and a clear refusal message."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DRIVERS = ROOT / "scripts" / "dev-tools"
BYPASSES = re.compile(
    r"ignore-certificate-errors|ignoreHTTPSErrors|acceptInsecureCerts|ignore-ssl-errors"
    r"|NODE_TLS_REJECT_UNAUTHORIZED|verify\s*=\s*False"
)


def test_drivers_and_source_never_disable_certificate_checks() -> None:
    offenders = [
        f"{p.relative_to(ROOT)}:{n}"
        for folder in (ROOT / "scripts", ROOT / "src")
        for p in folder.rglob("*")
        if p.suffix in {".mjs", ".js", ".py", ".ts"}
        for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1)
        if BYPASSES.search(line)
    ]
    assert offenders == []


def test_the_image_ships_every_module_the_drivers_import() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text()
    copied = set(re.findall(r"scripts/dev-tools/([\w.-]+\.mjs)", dockerfile))
    for driver in ("chrome_capture.mjs", "playbook_runner.mjs"):
        assert driver in copied
        local = re.findall(r'from "\./([\w.-]+\.mjs)"', (DRIVERS / driver).read_text())
        assert local == ["tls_errors.mjs"]
        assert set(local) <= copied


def _describe(error_js: str) -> str:
    node = shutil.which("node")
    assert node, "node is required (the Fluent SDK and the drivers run on it)"
    script = (
        f"import {{ describeLoadError }} from {json.dumps((DRIVERS / 'tls_errors.mjs').as_uri())};"
        f"process.stdout.write(describeLoadError({error_js}));"
    )
    done = subprocess.run(
        [node, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return done.stdout


@pytest.mark.parametrize(
    ("error_js", "code"),
    [
        (
            "new Error('net::ERR_CERT_AUTHORITY_INVALID at https://x.service-now.com')",
            "ERR_CERT_AUTHORITY_INVALID",
        ),
        ("new Error('net::ERR_CERT_DATE_INVALID at https://x')", "ERR_CERT_DATE_INVALID"),
        ("new Error('net::ERR_SSL_PROTOCOL_ERROR at https://x')", "ERR_SSL_PROTOCOL_ERROR"),
        ("'net::ERR_BAD_SSL_CLIENT_AUTH_CERT'", "ERR_BAD_SSL_CLIENT_AUTH_CERT"),
    ],
)
def test_describe_load_error_names_a_refused_certificate(error_js: str, code: str) -> None:
    assert _describe(error_js) == (
        f"The instance's TLS certificate was refused ({code}); nothing was captured. "
        "Check the instance URL, or fix the certificate."
    )


@pytest.mark.parametrize(
    ("error_js", "expected"),
    [
        (
            "new Error('net::ERR_NAME_NOT_RESOLVED at https://x')",
            "net::ERR_NAME_NOT_RESOLVED at https://x",
        ),
        (
            "new Error('Navigation timeout of 30000 ms exceeded')",
            "Navigation timeout of 30000 ms exceeded",
        ),
        ("'plain text'", "plain text"),
    ],
)
def test_describe_load_error_keeps_other_messages(error_js: str, expected: str) -> None:
    assert _describe(error_js) == expected
