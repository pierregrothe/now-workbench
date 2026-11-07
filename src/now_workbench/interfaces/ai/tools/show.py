# src/now_workbench/interfaces/ai/tools/show.py
# The `show` tool: Otto presents visual aids from a catalog of entity and generic tiles.
# Author: Pierre Grothe
# Date: 2026-11-07
"""Visual tile catalog (ADR-025).

Entity tiles name a record; the server loads it for the signed-in person through the same
read tools Otto uses, so what the tile shows is the record, never Otto's paraphrase of it.
Generic tiles carry what Otto writes (an explanation, a comparison, the steps of a plan),
checked against a strict schema. When Otto calls `show` in a reply, the reply shows what it
chose instead of every tile its tools returned.
"""

from collections.abc import Callable
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from now_workbench.domains.instances import InstanceRepository
from now_workbench.domains.seed import SeedRepository
from now_workbench.interfaces.ai.tiles import TileLayout, UITileSpec
from now_workbench.interfaces.ai.tools.base import (
    ToolContext,
    ToolResult,
    ToolSpec,
    register,
    resolve_instance,
    table_tile,
)
from now_workbench.interfaces.ai.tools.bundles import _get_runbook, _inspect_bundle
from now_workbench.interfaces.ai.tools.captures import _list_demo_captures
from now_workbench.interfaces.ai.tools.charts import MAX_POINTS, ChartSpec
from now_workbench.interfaces.ai.tools.sharing import _list_shares

__all__ = ["TileRequest"]

Tone = Literal["neutral", "good", "warn", "bad"]
_MAX_TILES = 6


class _Action(BaseModel):
    """A follow-up the person can click; it is sent to Otto as their next message."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str = Field(min_length=1, max_length=40)
    prompt: str = Field(min_length=1, max_length=300)


class _Base(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(default="", max_length=80)
    actions: list[_Action] = Field(default_factory=list, max_length=4)
    span: Literal[1, 2, 3] | None = None


# --- generic tiles: content Otto writes ----------------------------------------------------


class TextTile(_Base):
    kind: Literal["text"]
    body: str = Field(min_length=1, max_length=2000)


class TableTile(_Base):
    kind: Literal["table"]
    columns: list[str] = Field(min_length=1, max_length=8)
    rows: list[list[str | int | float | bool | None]] = Field(max_length=50)


class Kpi(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str = Field(min_length=1, max_length=40)
    value: str = Field(min_length=1, max_length=40)
    tone: Tone = "neutral"
    hint: str = Field(default="", max_length=80)
    # A small trend line drawn under the value (oldest first), ADR-027.
    trend: list[float] = Field(default_factory=list, max_length=MAX_POINTS)


class KpisTile(_Base):
    kind: Literal["kpis"]
    items: list[Kpi] = Field(min_length=1, max_length=8)


class Step(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    label: str = Field(min_length=1, max_length=120)
    status: Literal["done", "running", "todo", "failed", "skipped"] = "todo"
    detail: str = Field(default="", max_length=200)


class StepsTile(_Base):
    kind: Literal["steps"]
    items: list[Step] = Field(min_length=1, max_length=20)


class Column(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    heading: str = Field(min_length=1, max_length=60)
    points: list[str] = Field(min_length=1, max_length=8)


class ComparisonTile(_Base):
    kind: Literal["comparison"]
    columns: list[Column] = Field(min_length=2, max_length=4)


class CalloutTile(_Base):
    kind: Literal["callout"]
    body: str = Field(min_length=1, max_length=600)
    tone: Literal["info", "success", "warning", "danger"] = "info"


class ChartTile(_Base, ChartSpec):
    kind: Literal["chart"]


# --- entity tiles: records the server loads --------------------------------------------------


class InstanceTile(_Base):
    kind: Literal["instance"]
    instance: str = Field(description="Instance name or id")


class BundleTile(_Base):
    kind: Literal["bundle", "runbook", "captures", "shares"]
    bundle_id: str


class SeedRunTile(_Base):
    kind: Literal["seed_run"]
    operation_id: str


class DiagnosticsTile(_Base):
    kind: Literal["diagnostics"]


TileRequest = Annotated[
    TextTile
    | TableTile
    | KpisTile
    | StepsTile
    | ComparisonTile
    | CalloutTile
    | ChartTile
    | InstanceTile
    | BundleTile
    | SeedRunTile
    | DiagnosticsTile,
    Field(discriminator="kind"),
]
_TILES = TypeAdapter(list[TileRequest])


def _with(tile: UITileSpec, req: _Base, n: int) -> UITileSpec:
    """Give a tile a unique id, Otto's title (when set) and its follow-up actions."""
    props = dict(tile.props)
    if req.actions:
        props["actions"] = [{"id": "ask", **a.model_dump()} for a in req.actions]
    return tile.model_copy(
        update={
            "id": f"tile-show-{n}-{tile.id}",
            "title": req.title or tile.title,
            "props": props,
            "span": req.span or tile.span,
        }
    )


def _generic(req: _Base) -> UITileSpec:
    data = req.model_dump(exclude={"title", "actions", "span"})
    kind = data.pop("kind")
    if kind == "table":
        return table_tile("table", req.title, data["columns"], data["rows"])
    tile_type = {"text": "rich-text"}.get(kind, kind)
    return UITileSpec(id=kind, type=tile_type, title=req.title, props=data)


_Handler = Callable[[ToolContext, dict[str, Any]], ToolResult]


def _tool_tiles(ctx: ToolContext, handler: _Handler, args: dict[str, Any]) -> list[UITileSpec]:
    """Tiles of a read tool: the same data the tool gives Otto, or its refusal."""
    res = handler(ctx, args)
    if not res.ok:
        raise ValueError(res.summary)
    return list(res.tiles)


def _instance(ctx: ToolContext, ref: str) -> list[UITileSpec]:
    inst = resolve_instance(ctx.conn, ref)
    public = inst.to_public(InstanceRepository(ctx.conn).get_instance_profile(inst.id))
    return [UITileSpec(id="instance", type="instance", props=public.model_dump(mode="json"))]


def _seed_run(ctx: ToolContext, op_id: str) -> list[UITileSpec]:
    op = SeedRepository(ctx.conn).get_seed_operation(op_id)
    if op is None:
        raise ValueError(f"No seed run '{op_id}'.")
    rows = [[r.table, r.sys_id] for r in op.created_records]
    title = f"Seed run {op.id}: {op.status}, {len(rows)} record(s)"
    return [table_tile("seed-run", title, ["Table", "sys_id"], rows)]


_BUNDLE_VIEWS: dict[str, _Handler] = {
    "bundle": _inspect_bundle,
    "runbook": _get_runbook,
    "captures": _list_demo_captures,
    "shares": _list_shares,
}


def _entity(ctx: ToolContext, req: _Base) -> list[UITileSpec]:
    match req:
        case InstanceTile(instance=ref):
            return _instance(ctx, ref)
        case BundleTile(kind=kind, bundle_id=bundle_id):
            return _tool_tiles(ctx, _BUNDLE_VIEWS[kind], {"bundle_id": bundle_id})
        case SeedRunTile(operation_id=op_id):
            return _seed_run(ctx, op_id)
        case _:
            return [UITileSpec(id="diagnostics", type="diagnostics")]


_GENERIC = (TextTile, TableTile, KpisTile, StepsTile, ComparisonTile, CalloutTile, ChartTile)


def _show(ctx: ToolContext, args: dict[str, Any]) -> ToolResult:
    try:
        requests = _TILES.validate_python(args.get("tiles") or [])
    except ValidationError as exc:
        return ToolResult(summary=f"Invalid tiles, nothing shown: {exc}", ok=False)
    if not requests:
        return ToolResult(summary="No tiles given.", ok=False)
    tiles: list[UITileSpec] = []
    problems: list[str] = []
    for n, req in enumerate(requests[:_MAX_TILES]):
        try:
            made = [_generic(req)] if isinstance(req, _GENERIC) else _entity(ctx, req)
        except Exception as exc:
            problems.append(f"{req.kind}: {exc}")
            continue
        tiles += [_with(t, req, n) for t in made]
    layout: TileLayout = args.get("layout") or "auto"
    summary = f"Showing {len(tiles)} tile(s)." + (
        f" Not shown: {'; '.join(problems)}" if problems else ""
    )
    return ToolResult(summary=summary, ok=bool(tiles), tiles=tiles, layout=layout, shown=True)


_KINDS = (
    "text {body}; table {columns, rows}; kpis {items:[{label, value, tone, hint, trend:[n]}]}; "
    "steps {items:[{label, status: done|running|todo|failed|skipped, detail}]}; "
    "comparison {columns:[{heading, points:[...]}]}; callout {body, tone: info|success|"
    "warning|danger}; instance {instance}; bundle|runbook|captures|shares {bundle_id}; "
    "seed_run {operation_id}; diagnostics {}; chart {chart: line|area|bar|pie|donut|meter, "
    "labels:[...], series:[{name, values:[n per label]}], unit, stacked; a meter takes value "
    "and max instead}. Charts: line or area for change over time, bar to compare categories, "
    "pie or donut for parts of one whole (one series, at most 8 slices), meter for progress "
    "against a limit; at most 8 series on one axis, never two measures of different scale"
)

register(
    ToolSpec(
        name="show",
        description=(
            "Show the person visual tiles: use them as visual aids whenever a picture helps "
            "more than a sentence. Entity tiles (instance, bundle, runbook, captures, shares, "
            "seed_run, diagnostics) are loaded from the record, so prefer them when talking "
            "about a record. Generic tiles carry your own words. Every tile takes an optional "
            "title, a span (1, 2 or 3 columns wide; the reply grid has 3 columns) and up to 4 "
            "actions {label, prompt} the person can click to ask a follow-up. "
            f"Kinds and fields: {_KINDS}. Once you call show, the reply displays only the tiles "
            "you showed."
        ),
        properties={
            "tiles": {
                "type": "array",
                "maxItems": _MAX_TILES,
                "items": {
                    "type": "object",
                    "properties": {"kind": {"type": "string"}},
                    "required": ["kind"],
                },
            },
            "layout": {"type": "string", "enum": ["1-col", "2-col", "3-col", "auto"]},
        },
        required=["tiles"],
        handler=_show,
        category="visual",
    )
)
