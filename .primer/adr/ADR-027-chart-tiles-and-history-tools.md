# ADR-027: Chart Tiles and History Tools

**Status:** accepted 2026-11-07
**Date:** 2026-11-07
**Builds on:** ADR-013 (no fabricated data), ADR-024 (web component structure), ADR-025 (tool
set, tiles), ADR-026 (Actions screen)

## Context

The owner asked (2026-11-07) for tiles that show data as pie charts, donuts, historical graphs
and more. Otto's tile catalog had numbers (`kpis`) and tables, but nothing drawn, and the web
app has no chart library (its only runtime dependency is Lit). Otto also had no tool that
returns a figure over time, so a history chart would have had nothing true to draw.

## Decision

### 1. One `chart` tile, six forms

`show` gains a `chart` kind: `line` and `area` (change over time), `bar`, optionally `stacked`
(compare categories), `pie` and `donut` (parts of one whole) and `meter` (progress against a
limit). A `kpis` item can carry a `trend`, drawn as a sparkline. The schema lives in
`interfaces/ai/tools/charts.py` and is shared by `show` and the history tools, so the web
only receives charts it can draw:

- every series has one value per label; at most 60 points and 8 series;
- a pie or donut is one series of at most 8 non-negative slices; the server folds the rest
  into "Other" (`fold_slices`), since categorical colors are never cycled;
- one value axis; two measures of different scale are two charts;
- a meter needs `value` and `max`.

### 2. Drawn in plain SVG, no chart library

`<now-chart-tile>` (with `now-chart-geometry.ts` and `now-chart-tile-styles.ts`) draws every
form. Six forms with one mark spec do not justify a new dependency in the approved stack.
The marks follow the data-viz method: 2px lines, columns at most 24px wide with a 4px
rounded data end, a 2px surface gap between stacked segments and slices, a 10% wash under an
area, hairline grid, labels in text colors (never the series color).

- Lines, areas and sparklines are smoothed with cubic Beziers whose tangents are monotone
  (Fritsch-Carlson): the curve passes through every point and never overshoots, so a dip to
  zero never draws below zero and a peak never rises above its value. Smoothing changes the
  look, never the values (owner's request, 2026-11-07).
- Colors: the validated eight-slot categorical palette in fixed order (worst adjacent CVD
  dE 9.1, normal vision 19.6 on white). Three slots are below 3:1 contrast on white, so
  every chart has a "Show data" table view. The meter uses the reserved status colors
  (under 70% good, under 90% warning, else critical), always with words.
- Hover: a crosshair and one tooltip listing every series on lines and areas; a band
  highlight and the same tooltip on bars; slice lift and a legend row on pies and donuts.
- Accessibility: each chart is an image with a one-line description; the meter is an ARIA
  `meter`; the legend is present for two or more series.

### 3. History tools that read the person's own data

Category `history`, so they also appear on the Actions screen (ADR-026):

- `usage_history {days}`: questions per day (area), tokens by conversation (donut) and,
  inside a conversation, its token budget (meter).
- `seed_activity {days}`: seed runs per day, stacked by outcome (completed, failed, rolled
  back, ...), statuses in a fixed order so each keeps its color.

A day without activity is a zero, never an estimate (ADR-013). The figures come from new
owner-scoped repository queries, `ThreadRepository.daily_question_counts` and
`SeedRepository.daily_status_counts`. The system prompt tells Otto to chart only figures it
got from a tool.

### 4. Duplicate tool names fail loudly

The registry refused nothing, so a second tool with a taken name silently replaced the
first. `seed_history` already existed (it lists past runs), and `delete_bundle` had been
registered twice. `register` now raises on a duplicate; the dead `delete_bundle`
registration is gone.

## Consequences

- Otto has 72 tools; charts work in replies and on the Actions screen.
- Token use is stored per conversation, not per reply, so tokens per day cannot be charted
  yet; that needs a per-reply usage record.
- Live instance figures (records per table, incidents over time) are not covered; they
  would be live queries against the instance, in a later change.
- Light theme only, like the rest of the app; a dark theme would need its own validated
  palette steps.
