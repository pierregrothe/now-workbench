# src/now_workbench/sdk/project.py
# Turns a demo bundle's Fluent sources into a buildable, deployable ServiceNow SDK project.
# Author: Pierre Grothe
# Date: 2026-11-06
"""Fluent SDK project generation (ADR-022).

Demo bundles carry Fluent sources but are not SDK projects. To deploy one, a project is
generated per bundle and instance vendor:

* scope ``x_<vendor>_<6 hex of the bundle id>``: unique per bundle, at most 18 characters,
  starting with the instance's vendor prefix (``glide.appcreator.company.code``);
* every custom table is renamed into that scope (``x_demo_ai_log`` -> ``x_snc_1a2b3c_ai_log``)
  in the Fluent sources; the same map is applied to seed records and runbook stages;
* the project lives in ``<workspace>/sdk-projects/<bundle>-<scope>`` and links to one shared
  SDK toolchain (``<workspace>/sdk-toolchain/node_modules``), installed once, because each
  install is hundreds of megabytes.
"""

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "SdkProject",
    "SdkProjectError",
    "prepare_project",
    "scope_for",
    "table_map_for",
]

_TABLE_NAME = re.compile(r"""name:\s*['"](x_[a-z0-9]+_[a-z0-9_]+)['"]""")
_FOREIGN_PREFIX = re.compile(r"^x_[a-z0-9]+_")
_MAX_TABLE = 80
_TOOLCHAIN_PACKAGES = ("@servicenow/sdk", "@servicenow/glide")


class SdkProjectError(RuntimeError):
    """The SDK project could not be generated or built."""


@dataclass(frozen=True)
class SdkProject:
    """A generated project ready for ``now-sdk install``.

    Attributes:
        path: Project directory.
        scope: Application scope.
        table_map: Original table name -> table name inside the scope.
    """

    path: Path
    scope: str
    table_map: dict[str, str]


def scope_for(bundle_id: str, vendor: str) -> str:
    """Return the application scope for a bundle on an instance with ``vendor`` prefix.

    Raises:
        SdkProjectError: The vendor prefix is not a short lowercase identifier.
    """
    clean = vendor.strip().lower()
    if not re.fullmatch(r"[a-z0-9]{1,8}", clean):
        raise SdkProjectError(f"Unusable vendor prefix '{vendor}' on the instance.")
    return f"x_{clean}_{hashlib.sha256(bundle_id.encode()).hexdigest()[:6]}"


def table_map_for(sources: list[str], scope: str) -> dict[str, str]:
    """Map every table declared in the Fluent sources into ``scope``."""
    mapping: dict[str, str] = {}
    for text in sources:
        for old in _TABLE_NAME.findall(text):
            if old.startswith(f"{scope}_"):
                continue
            mapping[old] = f"{scope}_{_FOREIGN_PREFIX.sub('', old)}"[:_MAX_TABLE]
    return mapping


def _rename(text: str, table_map: dict[str, str]) -> str:
    for old in sorted(table_map, key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(old)}\b", table_map[old], text)
    return text


async def _run(cmd: list[str], cwd: Path, timeout_s: float = 600.0) -> str:
    """Run a command and return its output; raise with the tail of it on failure."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except TimeoutError as exc:
        proc.kill()
        raise SdkProjectError(f"'{' '.join(cmd[:2])}' timed out after {timeout_s:.0f}s") from exc
    text = out.decode("utf-8", "replace")
    if proc.returncode != 0:
        tail = " | ".join(line for line in text.strip().splitlines()[-4:])
        raise SdkProjectError(f"'{' '.join(cmd[:2])}' failed: {tail}")
    return text


async def _ensure_toolchain(workspace: Path, package_json: Path) -> Path:
    """Install the SDK packages once and return the shared node_modules directory."""
    toolchain = workspace / "sdk-toolchain"
    modules = toolchain / "node_modules"
    if all((modules / pkg / "package.json").exists() for pkg in _TOOLCHAIN_PACKAGES):
        return modules
    toolchain.mkdir(parents=True, exist_ok=True)
    project_pkg = json.loads(package_json.read_text(encoding="utf-8"))
    manifest = {
        "name": "workbench-sdk-toolchain",
        "private": True,
        "devDependencies": project_pkg.get("devDependencies", {}),
    }
    (toolchain / "package.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    await _run(["npm", "install", "--no-audit", "--no-fund"], toolchain)
    return modules


async def prepare_project(
    bundle_dir: Path,
    bundle_id: str,
    app_name: str,
    vendor: str,
    workspace: Path,
    now_sdk: str = "now-sdk",
) -> SdkProject:
    """Generate (or refresh) and build the SDK project for a bundle.

    Args:
        bundle_dir: The bundle directory (its ``fluent/*.now.ts`` are the sources).
        bundle_id: Bundle id (determines the scope).
        app_name: Application name shown on the instance.
        vendor: The instance's vendor prefix.
        workspace: Writable workspace directory.
        now_sdk: The now-sdk executable.

    Returns:
        The built project.

    Raises:
        SdkProjectError: No Fluent sources, or init, install or build failed.
    """
    sources = sorted((bundle_dir / "fluent").glob("*.now.ts"))
    if not sources:
        raise SdkProjectError("The bundle has no Fluent sources (fluent/*.now.ts).")
    scope = scope_for(bundle_id, vendor)
    texts = [s.read_text(encoding="utf-8") for s in sources]
    table_map = table_map_for(texts, scope)

    project = workspace / "sdk-projects" / f"{bundle_id}-{scope}"
    if not (project / "package.json").exists():
        project.mkdir(parents=True, exist_ok=True)
        package = re.sub(r"[^a-z0-9-]+", "-", bundle_id.lower()).strip("-") or "demo-app"
        await _run(
            [
                now_sdk,
                "init",
                "--appName",
                app_name[:80] or bundle_id,
                "--packageName",
                package,
                "--scopeName",
                scope,
                "--template",
                "base",
            ],
            project,
        )
    fluent_dir = project / "src" / "fluent"
    fluent_dir.mkdir(parents=True, exist_ok=True)
    for stale in fluent_dir.glob("*.now.ts"):
        stale.unlink()
    for source, text in zip(sources, texts, strict=True):
        (fluent_dir / source.name).write_text(_rename(text, table_map), encoding="utf-8")

    modules = await _ensure_toolchain(workspace, project / "package.json")
    link = project / "node_modules"
    if not link.exists():
        link.symlink_to(modules, target_is_directory=True)
    await _run([now_sdk, "build"], project)
    return SdkProject(path=project, scope=scope, table_map=table_map)
