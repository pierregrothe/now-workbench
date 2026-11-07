# src/now_workbench/interfaces/ai/tools/charts.py
# Chart tile schema shared by the `show` tool and the history tools (ADR-027).
# Author: Pierre Grothe
# Date: 2026-11-07
"""Chart tiles: line, area, bar, pie, donut and meter.

One schema checks both what Otto writes and what the history tools build, so the web
renderer only ever receives a chart it can draw. The rules follow the data-viz method:
at most eight series (categorical colors are never cycled), one value axis, and a pie or
donut is one series of at most eight non-negative slices (the rest fold into "Other").
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from now_workbench.interfaces.ai.tiles import UITileSpec

__all__ = ["chart_tile", "fold_slices", "ChartSeries", "ChartSpec"]

ChartForm = Literal["line", "area", "bar", "pie", "donut", "meter"]
MAX_SERIES = 8
MAX_POINTS = 60
_ROUND = ("pie", "donut")


class ChartSeries(BaseModel):
    """One named series: a value per label."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=40)
    values: list[float] = Field(max_length=MAX_POINTS)


class ChartSpec(BaseModel):
    """What a chart shows; `meter` uses value and max, every other form labels and series."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chart: ChartForm
    labels: list[str] = Field(default_factory=list, max_length=MAX_POINTS)
    series: list[ChartSeries] = Field(default_factory=list, max_length=MAX_SERIES)
    unit: str = Field(default="", max_length=12)
    stacked: bool = False
    value: float | None = None
    max: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _check_shape(self) -> Self:
        if self.chart == "meter":
            if self.value is None or self.max is None:
                raise ValueError("a meter needs value and max")
            return self
        if not self.labels or not self.series:
            raise ValueError(f"a {self.chart} chart needs labels and series")
        if any(len(s.values) != len(self.labels) for s in self.series):
            raise ValueError("every series needs one value per label")
        if self.chart in _ROUND:
            if len(self.series) != 1 or len(self.labels) > MAX_SERIES:
                raise ValueError(f"a {self.chart} is one series of at most {MAX_SERIES} slices")
            if any(v < 0 for v in self.series[0].values):
                raise ValueError(f"a {self.chart} cannot show negative values")
        return self


def fold_slices(pairs: list[tuple[str, float]]) -> tuple[list[str], list[float]]:
    """Keep the seven largest slices and fold the rest into "Other".

    Args:
        pairs: (label, value) slices in any order.

    Returns:
        Labels and values, largest first, at most eight slices.
    """
    ranked = sorted(pairs, key=lambda p: p[1], reverse=True)
    if len(ranked) > MAX_SERIES:
        ranked = [*ranked[: MAX_SERIES - 1], ("Other", sum(v for _, v in ranked[MAX_SERIES - 1 :]))]
    return [label for label, _ in ranked], [value for _, value in ranked]


def chart_tile(tile_id: str, title: str, spec: ChartSpec, span: int | None = None) -> UITileSpec:
    """Build the tile the web renderer draws for a chart.

    Args:
        tile_id: Tile id, unique within the reply.
        title: Heading shown above the chart.
        spec: The validated chart.
        span: Columns (of three) the tile spans; None follows the reply layout.

    Returns:
        A `chart` tile.
    """
    return UITileSpec(
        id=tile_id, type="chart", title=title, props=spec.model_dump(mode="json"), span=span
    )
