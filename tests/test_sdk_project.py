# tests/test_sdk_project.py
# Generating a deployable Fluent SDK project from a demo bundle (ADR-022).
# Author: Pierre Grothe
# Date: 2026-11-06
"""Tests for now_workbench.sdk.project and the pipeline's deploy step."""

import json
import os
import shutil
from pathlib import Path

import pytest

from now_workbench.bundles import pipeline as pipeline_mod
from now_workbench.bundles.pipeline import DemoPipelineEngine, PipelineStepError
from now_workbench.db import InstanceCreate, db_session
from now_workbench.db.repos.instances import InstanceRepository
from now_workbench.properties.engine import PropertyEngine
from now_workbench.sdk.project import (
    SdkProject,
    SdkProjectError,
    prepare_project,
    scope_for,
    table_map_for,
)
from now_workbench.sdk.runner import SdkExecutionResult

REPO = Path(__file__).resolve().parents[1]

# Stand-in for now-sdk: `init` writes package.json from its flags; `build` checks the sources.
_FAKE_SDK = """#!/bin/sh
case "$1" in
  init)
    scope=""; while [ $# -gt 0 ]; do [ "$1" = --scopeName ] && scope="$2"; shift; done
    printf '{"name":"p","devDependencies":{"@servicenow/sdk":"4.14.0"}}' > package.json
    printf '{"scope":"%s"}' "$scope" > now.config.json ;;
  build)
    ls src/fluent/*.now.ts > /dev/null || exit 3
    [ -d node_modules/@servicenow/sdk ] || exit 4
    echo built ;;
  *) exit 9 ;;
esac
"""

# Stand-in for npm install: creates the two toolchain packages.
_FAKE_NPM = """#!/bin/sh
for p in @servicenow/sdk @servicenow/glide; do
  mkdir -p "node_modules/$p" && echo '{}' > "node_modules/$p/package.json"
done
echo "npm-ran" >> ../npm-calls.log
"""


@pytest.fixture
def tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Put stand-in now-sdk and npm executables first on PATH."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("now-sdk", _FAKE_SDK), ("npm", _FAKE_NPM)):
        exe = bin_dir / name
        exe.write_text(body, encoding="utf-8")
        exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    return bin_dir


def test_scope_for_is_short_unique_and_vendor_prefixed() -> None:
    """A scope starts with the vendor prefix, fits 18 characters and differs per bundle."""
    a, b = scope_for("hr-onboarding-ai", "snc"), scope_for("sample-ai-assistant", "SNC")
    assert a.startswith("x_snc_") and len(a) <= 18
    assert a != b
    with pytest.raises(SdkProjectError, match="vendor prefix"):
        scope_for("x", "not a prefix!")


def test_table_map_for_moves_tables_into_the_scope() -> None:
    """Foreign prefixes are replaced; tables already in the scope are left alone."""
    src = "Table({ name: 'x_demo_ai_routing_log' }) Table({ name: \"x_snc_ab12cd_kept\" })"
    assert table_map_for([src], "x_snc_ab12cd") == {
        "x_demo_ai_routing_log": "x_snc_ab12cd_ai_routing_log"
    }


async def test_prepare_project_generates_renames_and_builds_once(
    tmp_path: Path, tools: Path
) -> None:
    """init runs once, sources are renamed, npm installs once and is shared, build runs."""
    bundle = tmp_path / "bundle"
    shutil.copytree(REPO / "bundles" / "sample-ai-assistant", bundle)
    workspace = tmp_path / "ws"
    project = await prepare_project(bundle, "sample-ai-assistant", "Demo", "snc", workspace)
    assert isinstance(project, SdkProject)
    generated = (project.path / "src" / "fluent" / "app.now.ts").read_text(encoding="utf-8")
    new_name = project.table_map["x_demo_ai_routing_log"]
    assert new_name.startswith(f"{project.scope}_")
    assert f"'{new_name}'" in generated and "x_demo_ai_routing_log" not in generated
    assert json.loads((project.path / "now.config.json").read_text())["scope"] == project.scope
    assert (project.path / "node_modules").is_symlink()

    again = await prepare_project(bundle, "sample-ai-assistant", "Demo", "snc", workspace)
    assert again.path == project.path
    calls = (workspace / "npm-calls.log").read_text(encoding="utf-8").splitlines()
    assert calls == ["npm-ran"]


async def test_prepare_project_relinks_a_removed_toolchain(
    tmp_path: Path, tools: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A project linked to a toolchain that was deleted is relinked to the current one."""
    bundle = tmp_path / "bundle"
    shutil.copytree(REPO / "bundles" / "sample-ai-assistant", bundle)
    workspace = tmp_path / "ws"
    project = await prepare_project(bundle, "sample-ai-assistant", "Demo", "snc", workspace)
    shutil.rmtree(workspace / "sdk-toolchain")
    image_modules = tmp_path / "global"
    for pkg in ("@servicenow/sdk", "@servicenow/glide"):
        (image_modules / pkg).mkdir(parents=True)
        (image_modules / pkg / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("WORKBENCH_SDK_NODE_MODULES", str(image_modules))
    await prepare_project(bundle, "sample-ai-assistant", "Demo", "snc", workspace)
    assert (project.path / "node_modules").readlink() == image_modules


async def test_prepare_project_without_sources_or_failing_build_raises(
    tmp_path: Path, tools: Path
) -> None:
    """No Fluent sources, or a failing SDK command, is reported with its reason."""
    empty = tmp_path / "empty"
    (empty / "fluent").mkdir(parents=True)
    with pytest.raises(SdkProjectError, match="no Fluent sources"):
        await prepare_project(empty, "e", "E", "snc", tmp_path / "ws")
    (tools / "now-sdk").write_text("#!/bin/sh\necho 'boom: bad schema'\nexit 1\n", "utf-8")
    bundle = tmp_path / "bundle"
    shutil.copytree(REPO / "bundles" / "sample-ai-assistant", bundle)
    with pytest.raises(SdkProjectError, match="boom: bad schema"):
        await prepare_project(bundle, "b", "B", "snc", tmp_path / "ws2")


class _OkRunner:
    def __init__(self, fake_mode: bool = False) -> None:
        self.fake_mode = fake_mode

    async def deploy(self, **kwargs: object) -> SdkExecutionResult:
        return SdkExecutionResult(command="deploy", exit_code=0, output="ok", success=True)


async def test_deploy_and_seed_generates_app_and_seeds_into_its_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On a real instance the app is generated in the vendor's scope and seeds follow."""
    bundles = tmp_path / "bundles"
    shutil.copytree(REPO / "bundles" / "hr-onboarding-ai", bundles / "hr-onboarding-ai")
    seen: dict[str, object] = {}
    posted: list[str] = []

    async def vendor(self: PropertyEngine, names: list[str], instance: object) -> dict:
        return {names[0]: "snc"}

    async def fake_prepare(bundle_dir: Path, bundle_id: str, name: str, v: str, ws: Path):
        seen["vendor"] = v
        return SdkProject(
            path=tmp_path, scope="x_snc_aaaaaa", table_map={"x_snc_hr_onboarding_ai_case": "x_t"}
        )

    monkeypatch.setattr(PropertyEngine, "read_live_values", vendor)
    monkeypatch.setattr(pipeline_mod, "prepare_project", fake_prepare)
    monkeypatch.setattr(pipeline_mod, "NowSdkRunner", _OkRunner)
    with db_session(tmp_path / "t.db") as conn:
        inst = InstanceRepository(conn).add_instance(
            InstanceCreate(id="i1", name="Real", url="https://real.service-now.com", password="p")
        )
        engine = DemoPipelineEngine(bundles_dir=bundles, conn=conn)

        async def fake_post(self: object, client: object, i: object, table: str, f: object) -> str:
            posted.append(table)
            return "sys1"

        monkeypatch.setattr(pipeline_mod.SeedEngine, "_post_record", fake_post)
        seed, note, renames = await engine.deploy_and_seed("hr-onboarding-ai", inst)
    assert seen["vendor"] == "snc"
    assert "scope x_snc_aaaaaa" in note
    assert "x_t" in posted and "x_snc_hr_onboarding_ai_case" not in posted
    assert renames == {"x_snc_hr_onboarding_ai_case": "x_t"}
    assert seed.status == "completed"


async def test_deploy_and_seed_without_vendor_prefix_stops_with_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the instance's vendor prefix cannot be read, the pipeline says so."""
    bundles = tmp_path / "bundles"
    shutil.copytree(REPO / "bundles" / "hr-onboarding-ai", bundles / "hr-onboarding-ai")

    async def no_vendor(self: PropertyEngine, names: list[str], instance: object) -> dict:
        return {names[0]: None}

    monkeypatch.setattr(PropertyEngine, "read_live_values", no_vendor)
    with db_session(tmp_path / "t.db") as conn:
        inst = InstanceRepository(conn).add_instance(
            InstanceCreate(id="i1", name="Real", url="https://real.service-now.com", password="p")
        )
        engine = DemoPipelineEngine(bundles_dir=bundles, conn=conn)
        with pytest.raises(PipelineStepError, match="vendor prefix"):
            await engine.deploy_and_seed("hr-onboarding-ai", inst)


async def test_deploy_and_seed_build_failure_stops_with_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Fluent build error stops the pipeline and carries the SDK's message."""
    bundles = tmp_path / "bundles"
    shutil.copytree(REPO / "bundles" / "hr-onboarding-ai", bundles / "hr-onboarding-ai")

    async def vendor(self: PropertyEngine, names: list[str], instance: object) -> dict:
        return {names[0]: "snc"}

    async def broken(*_args: object, **_kwargs: object) -> SdkProject:
        raise SdkProjectError("'now-sdk build' failed: bad column")

    monkeypatch.setattr(PropertyEngine, "read_live_values", vendor)
    monkeypatch.setattr(pipeline_mod, "prepare_project", broken)
    with db_session(tmp_path / "t.db") as conn:
        inst = InstanceRepository(conn).add_instance(
            InstanceCreate(id="i1", name="Real", url="https://real.service-now.com", password="p")
        )
        engine = DemoPipelineEngine(bundles_dir=bundles, conn=conn)
        with pytest.raises(PipelineStepError, match="bad column"):
            await engine.deploy_and_seed("hr-onboarding-ai", inst)


async def test_deploy_and_seed_without_fluent_sources_skips_deploy(tmp_path: Path) -> None:
    """A bundle with no Fluent sources is only seeded."""
    bundles = tmp_path / "bundles"
    shutil.copytree(REPO / "bundles" / "hr-onboarding-ai", bundles / "b")
    shutil.rmtree(bundles / "b" / "fluent")
    with db_session(tmp_path / "t.db") as conn:
        inst = InstanceRepository(conn).add_instance(
            InstanceCreate(id="i1", name="Fake", url="fake://f.service-now.com", password="p")
        )
        engine = DemoPipelineEngine(bundles_dir=bundles, conn=conn)
        _seed, note, renames = await engine.deploy_and_seed("b", inst, fake_mode=True)
    assert note.startswith("Deploy skipped") and renames == {}


async def test_test_demo_script_checks_renamed_tables(tmp_path: Path) -> None:
    """Runbook stages aimed at a renamed table are checked against the new name."""
    bundles = tmp_path / "bundles"
    shutil.copytree(REPO / "bundles" / "hr-onboarding-ai", bundles / "hr-onboarding-ai")
    with db_session(tmp_path / "t.db") as conn:
        inst = InstanceRepository(conn).add_instance(
            InstanceCreate(id="i1", name="Fake", url="fake://f.service-now.com", password="p")
        )
        engine = DemoPipelineEngine(bundles_dir=bundles, conn=conn)
        res = await engine.test_demo_script(
            "hr-onboarding-ai",
            inst,
            fake_mode=True,
            table_map={"x_snc_hr_onboarding_ai_case": "x_snc_aaaaaa_hr_case"},
        )
    tables = {s.target_table for s in res.stages}
    assert "x_snc_aaaaaa_hr_case" in tables
    assert "x_snc_hr_onboarding_ai_case" not in tables


async def test_run_command_that_hangs_times_out(tmp_path: Path) -> None:
    """A stuck SDK or npm command is stopped and reported, never waited on forever."""
    from now_workbench.sdk import project as project_mod

    with pytest.raises(SdkProjectError, match="timed out"):
        await project_mod._run(["sleep", "5"], tmp_path, timeout_s=0.2)


async def test_prepare_project_links_the_global_toolchain_without_installing(
    tmp_path: Path, tools: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With the image's global SDK packages present, nothing is downloaded."""
    global_modules = tmp_path / "global"
    for pkg in ("@servicenow/sdk", "@servicenow/glide"):
        (global_modules / pkg).mkdir(parents=True)
        (global_modules / pkg / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("WORKBENCH_SDK_NODE_MODULES", str(global_modules))
    bundle = tmp_path / "bundle"
    shutil.copytree(REPO / "bundles" / "sample-ai-assistant", bundle)
    workspace = tmp_path / "ws"
    project = await prepare_project(bundle, "sample-ai-assistant", "Demo", "snc", workspace)
    assert (project.path / "node_modules").resolve() == global_modules.resolve()
    assert not (workspace / "npm-calls.log").exists()
    assert not (workspace / "sdk-toolchain").exists()
