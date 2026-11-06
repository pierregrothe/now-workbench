# tests/test_capture_credentials.py
# Tests that capture credentials travel over stdin, never argv (ADR-012).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Credential hand-off tests for the Node capture scripts."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from now_workbench.capture.driver import _build_runner_cmd, encode_stdin_credentials
from now_workbench.db.models import InstanceRecord

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "dev-tools"


def test_build_runner_cmd_keeps_credentials_out_of_argv(tmp_path: Path) -> None:
    """The runner command line carries the stdin flag and no username or password."""
    inst = InstanceRecord(
        id="i-1", name="I", url="https://i.service-now.com", username="svc.user", password="S3cr3t!"
    )
    cmd = _build_runner_cmd(
        tmp_path / "runner.mjs",
        tmp_path / "pb.json",
        "https://i.service-now.com/now",
        tmp_path / "v.webm",
        tmp_path / "v.png",
        tmp_path / "log.json",
        tmp_path / "state.json",
        1280,
        720,
        inst,
    )
    joined = " ".join(cmd)
    assert "--credentials-stdin" in cmd
    assert "S3cr3t!" not in joined and "svc.user" not in joined
    assert "--password" not in cmd and "--username" not in cmd


def test_encode_stdin_credentials_is_json() -> None:
    """The stdin payload is a JSON object the Node scripts can parse."""
    payload = json.loads(encode_stdin_credentials("svc", "p\"w'd"))
    assert payload == {"username": "svc", "password": "p\"w'd"}


@pytest.mark.parametrize("script", ["chrome_capture.mjs", "playbook_runner.mjs"])
def test_node_scripts_read_credentials_from_stdin(script: str) -> None:
    """Both Node scripts define the stdin reader and no argv credential flags."""
    source = (_SCRIPTS / script).read_text(encoding="utf-8")
    assert "readStdinCredentials" in source
    assert "--credentials-stdin" in source
    assert '"--password"' not in source and '"--username"' not in source


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_node_stdin_reader_parses_payload(tmp_path: Path) -> None:
    """The reader shared by both scripts parses the payload Python sends."""
    source = (_SCRIPTS / "playbook_runner.mjs").read_text(encoding="utf-8")
    start = source.index("async function readStdinCredentials")
    end = source.index("\n}\n", start) + 3
    probe = tmp_path / "probe.mjs"
    probe.write_text(
        source[start:end] + "console.log(JSON.stringify(await readStdinCredentials()));\n",
        encoding="utf-8",
    )
    node = shutil.which("node")
    assert node is not None
    done = subprocess.run(
        [node, str(probe)],
        input=encode_stdin_credentials("svc", "S3cr3t!"),
        capture_output=True,
        check=True,
    )
    assert json.loads(done.stdout) == {"username": "svc", "password": "S3cr3t!"}
