"""Generative UI Tile Catalog schemas and tool-calling models."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

TileType = Literal[
    "instance-kpi",
    "instance-card",
    "demo-bundle",
    "security-alert",
    "fluent-schema",
    "rich-text",
    "data-table",
    "media-player",
    "instance",
    "diagnostics",
    "kpis",
    "steps",
    "comparison",
    "callout",
]

TileLayout = Literal["1-col", "2-col", "3-col", "auto"]


class UITileSpec(BaseModel):
    """Specification for a single Generative UI tile."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(description="Unique identifier for the tile")
    type: TileType = Field(description="Catalog type identifier for the tile")
    title: str = Field(default="", description="Optional human-readable title")
    props: dict[str, Any] = Field(
        default_factory=dict, description="Structured properties passed to the tile component"
    )
    span: int | None = Field(
        default=None,
        ge=1,
        le=3,
        description="Columns the tile spans (1-3); None follows the layout",
    )


class AgentStep(BaseModel):
    """One tool run Otto performed while answering, shown as a step in the conversation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str = Field(description="What the tool reported, in one line")
    ok: bool = Field(default=True, description="False when the tool run failed")


class GenerativeUIResponse(BaseModel):
    """Structured response containing executive summary, multi-tile layout, and tile specs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    summary: str = Field(
        description="Concise 1-sentence executive summary with no excessive markdown"
    )
    layout: TileLayout = Field(
        default="auto", description="Column layout arrangement for multi-tile rendering"
    )
    tiles: list[UITileSpec] = Field(
        default_factory=list, description="List of tiles to display in the session"
    )
    steps: list[AgentStep] = Field(
        default_factory=list, description="Tool runs performed to produce this response"
    )
    usage: dict[str, int] = Field(
        default_factory=dict, description="Claude tokens this reply used (ADR-023)"
    )
    # The exact messages exchanged with Claude for this reply, replayed unchanged on later
    # questions so the conversation is served from the prompt cache. Never sent to the UI.
    transcript: list[dict[str, Any]] = Field(default_factory=list, exclude=True)
