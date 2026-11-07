"""Shared tool registry primitives for the Otto agent (single source of truth for actions)."""

import asyncio
import concurrent.futures
import contextvars
import json
import sqlite3
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from now_workbench.domains.identity import AuthUser, current_actor
from now_workbench.domains.instances import InstanceRecord, InstanceRepository
from now_workbench.interfaces.ai.tiles import TileLayout, UITileSpec

# JSON schema of the bundle id argument most tools take.
BUNDLE_ARG: dict[str, str] = {
    "type": "string",
    "description": "Demo bundle id (slug, e.g. 'sample-ai-assistant').",
}


class ToolResult(BaseModel):
    """Outcome of executing a tool: text for the model plus tiles for the user."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    summary: str
    ok: bool = True
    pending: bool = False
    data: dict[str, Any] = Field(default_factory=dict)
    tiles: list[UITileSpec] = Field(default_factory=list)
    layout: TileLayout = "1-col"
    # Images Claude should see with the result (base64 PNG/JPEG), so Otto can check its own
    # work, e.g. that a screenshot shows the requested page and not a sign-in screen.
    images: list[str] = Field(default_factory=list, max_length=4)
    # Set by the `show` tool: these tiles were chosen by Otto as the reply's visuals (ADR-025).
    shown: bool = False


@dataclass
class ToolContext:
    """Execution context shared by all tools in one agent turn."""

    conn: sqlite3.Connection
    fake_mode: bool = False
    user: AuthUser | None = None

    def actor(self) -> AuthUser:
        """The person Otto acts for: the explicit user, else the request's (ADR-025)."""
        return self.user or current_actor()


ToolHandler = Callable[[ToolContext, dict[str, Any]], ToolResult]
ToolPlanner = Callable[[ToolContext, dict[str, Any]], str]


@dataclass(frozen=True)
class ToolSpec:
    """A callable action exposed to the Otto agent (mirrors a CLI/API capability)."""

    name: str
    description: str
    properties: dict[str, Any]
    handler: ToolHandler
    required: list[str] = field(default_factory=list)
    category: str = "general"
    cli_equivalent: str = ""
    destructive: bool = False
    plan: ToolPlanner | None = None

    def definition(self) -> dict[str, Any]:
        """Return the Anthropic tool definition for this spec."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.properties,
                "required": self.required,
            },
        }


REGISTRY: dict[str, ToolSpec] = {}


def register(spec: ToolSpec) -> ToolSpec:
    """Add a tool to the global registry."""
    REGISTRY[spec.name] = spec
    return spec


def run_async[T](coro: Awaitable[T]) -> T:
    """Run a coroutine to completion from synchronous code (thread-safe)."""

    async def _wrap() -> T:
        return await coro

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_wrap())
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        # Copy the context so the owner scope (ADR-018) follows the work into the thread.
        return pool.submit(contextvars.copy_context().run, asyncio.run, _wrap()).result()


def resolve_instance(conn: sqlite3.Connection, ref: str | None) -> InstanceRecord:
    """Resolve an instance by id, name, or URL fragment (default instance if blank)."""
    instance_repo = InstanceRepository(conn)
    if not ref:
        inst = instance_repo.get_default_instance()
        if not inst:
            raise ValueError("No default instance is configured.")
        return inst
    needle = ref.strip().lower()
    instances = instance_repo.list_instances()
    for inst in instances:
        if inst.id.lower() == needle or inst.name.lower() == needle:
            return inst
    partial = [i for i in instances if needle in i.name.lower() or needle in i.url.lower()]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        names = ", ".join(i.name for i in partial)
        raise ValueError(f"'{ref}' is ambiguous; it matches: {names}.")
    raise ValueError(f"No instance matches '{ref}'.")


def table_tile(
    tile_id: str,
    title: str,
    columns: list[str],
    rows: list[list[Any]],
    actions: list[dict[str, Any]] | None = None,
) -> UITileSpec:
    """Build a generic data-table tile."""
    return UITileSpec(
        id=tile_id,
        type="data-table",
        title=title,
        props={
            "columns": columns,
            "rows": [[str(c) for c in r] for r in rows],
            "actions": actions or [],
        },
    )


def text_tile(
    tile_id: str,
    title: str,
    body: str,
    actions: list[dict[str, Any]] | None = None,
) -> UITileSpec:
    """Build a rich-text tile."""
    return UITileSpec(
        id=tile_id,
        type="rich-text",
        title=title,
        props={"body": body, "actions": actions or []},
    )


def media_tile(
    tile_id: str,
    title: str,
    url: str,
    media_type: str = "video",
    label: str = "",
    actions: list[dict[str, Any]] | None = None,
) -> UITileSpec:
    """Build a media-player tile."""
    return UITileSpec(
        id=tile_id,
        type="media-player",
        title=title,
        props={
            "url": url,
            "media_type": media_type,
            "label": label,
            "actions": actions or [],
        },
    )


def model_to_text(payload: Any, limit: int = 4000) -> str:
    """Serialize tool data for the model, truncated to keep context small."""
    text = json.dumps(payload, default=str)
    return text if len(text) <= limit else text[:limit] + "...[truncated]"
