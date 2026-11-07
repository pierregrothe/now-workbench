// web/src/tiles/now-chart-tile.ts
// Chart tile: line, area, bar, pie, donut and meter drawn in plain SVG (ADR-027).
// Author: Pierre Grothe
// Date: 2026-11-07
//
// No chart library: the forms are few and the marks follow one spec (2px lines, 24px-max
// columns with a 4px rounded end, a 2px surface gap between fills, one value axis). Every
// value is reachable without hovering through the "Show data" table.

import { LitElement, html, svg, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import {
  SERIES_COLORS,
  STATUS_COLORS,
  type ChartProps,
  columnPath,
  fmtAxis,
  fmtValue,
  labelIndexes,
  smoothPath,
  meterStatus,
  niceTicks,
  slicePath,
  valueMax,
} from './now-chart-geometry.js';
import { chartTileStyles } from './now-chart-tile-styles.js';

const H = 200;
const PAD = { top: 12, right: 16, bottom: 24, left: 40 };
const ROUND = new Set(['pie', 'donut']);

@customElement('now-chart-tile')
export class NowChartTile extends LitElement {
  static styles = chartTileStyles;

  @property({ type: Object }) props!: ChartProps;
  @property() heading = '';

  @state() private width = 480;
  @state() private hover: number | null = null;
  @state() private showTable = false;

  private resizer = new ResizeObserver(([entry]) => {
    const w = Math.round(entry.contentRect.width);
    if (w > 0 && w !== this.width) this.width = w;
  });

  connectedCallback(): void {
    super.connectedCallback();
    this.resizer.observe(this);
  }

  disconnectedCallback(): void {
    this.resizer.disconnect();
    super.disconnectedCallback();
  }

  private get unit(): string {
    return this.props.unit ?? '';
  }

  /** One sentence a screen reader (and Otto's history) can read instead of the picture. */
  private describe(): string {
    const p = this.props;
    if (p.chart === 'meter') return `${fmtValue(p.value ?? 0, this.unit)} of ${fmtValue(p.max ?? 0, this.unit)}`;
    const names = p.series.map((s) => s.name).join(', ');
    return `${p.chart} chart of ${names} over ${p.labels.length} points, ${p.labels[0]} to ${p.labels[p.labels.length - 1]}`;
  }

  private onPointer(e: PointerEvent, plotW: number, n: number): void {
    const box = (e.currentTarget as SVGElement).getBoundingClientRect();
    const x = e.clientX - box.left - PAD.left;
    const slot = this.props.chart === 'bar' ? Math.floor((x / plotW) * n) : Math.round((x / plotW) * (n - 1));
    this.hover = Math.min(Math.max(slot, 0), n - 1);
  }

  private renderAxes(ticks: number[], y: (v: number) => number, plotW: number, xs: number[]) {
    const n = this.props.labels.length;
    const shown = labelIndexes(n, Math.max(2, Math.floor(plotW / 70)));
    return svg`
      ${ticks.map(
        (t) => svg`<line class="grid" x1=${PAD.left} x2=${PAD.left + plotW} y1=${y(t)} y2=${y(t)}></line>
          <text class="tick" x=${PAD.left - 6} y=${y(t) + 4} text-anchor="end">${fmtAxis(t)}</text>`
      )}
      <line class="baseline" x1=${PAD.left} x2=${PAD.left + plotW} y1=${y(0)} y2=${y(0)}></line>
      ${shown.map((i) => svg`<text class="tick" x=${xs[i]} y=${H - 6} text-anchor="middle">${this.props.labels[i]}</text>`)}
    `;
  }

  private renderCartesian() {
    const p = this.props;
    const n = p.labels.length;
    const plotW = Math.max(40, this.width - PAD.left - PAD.right);
    const plotH = H - PAD.top - PAD.bottom;
    const ticks = niceTicks(valueMax(p));
    const top = ticks[ticks.length - 1] || 1;
    const y = (v: number) => PAD.top + plotH - (Math.max(0, v) / top) * plotH;
    const isBar = p.chart === 'bar';
    const band = plotW / n;
    const xs = [...Array(n).keys()].map((i) => (isBar ? PAD.left + band * (i + 0.5) : PAD.left + (n === 1 ? plotW / 2 : (plotW * i) / (n - 1))));
    const marks = isBar ? this.renderBars(xs, band, y) : this.renderLines(xs, y);
    const h = this.hover;
    return html`<svg
        width=${this.width}
        height=${H}
        role="img"
        aria-label=${this.describe()}
        @pointermove=${(e: PointerEvent) => this.onPointer(e, plotW, n)}
        @pointerleave=${() => (this.hover = null)}
      >
        ${this.renderAxes(ticks, y, plotW, xs)} ${marks}
        ${h !== null && !isBar ? svg`<line class="crosshair" x1=${xs[h]} x2=${xs[h]} y1=${PAD.top} y2=${PAD.top + plotH}></line>` : nothing}
        ${h !== null && isBar ? svg`<rect class="band-hover" x=${PAD.left + band * h} y=${PAD.top} width=${band} height=${plotH}></rect>` : nothing}
      </svg>
      ${h !== null ? this.renderTooltip(h, xs[h]) : nothing}`;
  }

  private renderLines(xs: number[], y: (v: number) => number) {
    const p = this.props;
    const last = xs.length - 1;
    // End labels for up to four series; one that would sit on a label already drawn is left
    // to the tooltip and the table instead of overlapping.
    const labelled: number[] = [];
    return p.series.map((s, si) => {
      const color = SERIES_COLORS[si];
      const pts = s.values.map((v, i) => [xs[i], y(v)] as [number, number]);
      const curve = smoothPath(pts);
      const area = p.chart === 'area' ? `${curve}L${xs[last]},${y(0)}L${xs[0]},${y(0)}Z` : '';
      const endY = y(s.values[last]);
      const fits = p.series.length <= 4 && labelled.every((ly) => Math.abs(ly - endY) >= 14);
      if (fits) labelled.push(endY);
      const label = fits ? svg`<text class="end-label" x=${xs[last] - 6} y=${pts[last][1] - 9} text-anchor="end">${fmtAxis(s.values[last])}</text>` : nothing;
      return svg`
        ${area ? svg`<path d=${area} fill=${color} fill-opacity="0.1"></path>` : nothing}
        <path class="line" d=${curve} stroke=${color}></path>
        <circle class="dot" cx=${xs[last]} cy=${pts[last][1]} r="4" fill=${color}></circle>
        ${label}
        ${this.hover !== null ? svg`<circle class="dot" cx=${xs[this.hover]} cy=${pts[this.hover][1]} r="4" fill=${color}></circle>` : nothing}
      `;
    });
  }

  private renderBars(xs: number[], band: number, y: (v: number) => number) {
    const p = this.props;
    const groups = p.stacked ? 1 : p.series.length;
    const w = Math.max(2, Math.min(24, (band * 0.7) / groups - 2));
    return p.labels.map((_, i) => {
      let base = 0;
      const topIndex = p.stacked ? p.series.map((s) => s.values[i] > 0).lastIndexOf(true) : -1;
      return p.series.map((s, si) => {
        const v = Math.max(0, s.values[i] ?? 0);
        if (!v) return nothing;
        const x = p.stacked ? xs[i] - w / 2 : xs[i] - (groups * (w + 2)) / 2 + si * (w + 2) + 1;
        const y1 = y(base + v);
        // Stacked segments: a 2px surface gap between them; only the top one is rounded.
        const h = y(base) - y1 - (p.stacked && base > 0 ? 2 : 0);
        if (p.stacked) base += v;
        return svg`<path d=${columnPath(x, y1, w, h, !p.stacked || si === topIndex)} fill=${SERIES_COLORS[si]}></path>`;
      });
    });
  }

  private renderTooltip(i: number, x: number) {
    const p = this.props;
    // Beside the pointer, on the side with room, so the marks under it stay visible.
    const left = x > this.width / 2 ? Math.max(x - 182, 0) : Math.min(x + 12, this.width - 170);
    return html`<div class="tooltip" style="left:${left}px">
      <div class="tip-head">${p.labels[i]}</div>
      ${p.series.map(
        (s, si) => html`<div class="tip-row"><span class="key" style="background:${SERIES_COLORS[si]}"></span><strong>${fmtValue(s.values[i] ?? 0, this.unit)}</strong><span class="muted">${s.name}</span></div>`
      )}
    </div>`;
  }

  private renderRound() {
    const p = this.props;
    const values = p.series[0]?.values ?? [];
    const total = values.reduce((a, b) => a + b, 0);
    const size = Math.min(180, this.width * 0.5);
    const r = size / 2;
    const inner = p.chart === 'donut' ? r * 0.62 : 0;
    let angle = 0;
    const slices = values.map((v, i) => {
      const a0 = angle;
      angle += total > 0 ? (v / total) * Math.PI * 2 : 0;
      return { i, v, a0, a1: angle };
    });
    const h = this.hover;
    return html`<div class="round">
      <svg width=${size} height=${size} role="img" aria-label=${this.describe()} @pointerleave=${() => (this.hover = null)}>
        ${slices
          .filter((s) => s.v > 0)
          .map(
            (s) => svg`<path class="slice ${h === s.i ? 'lift' : ''}" d=${slicePath(r, r, r - 1, inner, s.a0, s.a1)} fill=${SERIES_COLORS[s.i]}
              @pointerenter=${() => (this.hover = s.i)}></path>`
          )}
        ${inner ? svg`<text class="center-value" x=${r} y=${r + 2} text-anchor="middle">${fmtAxis(h === null ? total : values[h])}</text>
          <text class="center-label" x=${r} y=${r + 18} text-anchor="middle">${h === null ? this.unit || 'total' : p.labels[h]}</text>` : nothing}
      </svg>
      <ul class="legend vertical">
        ${p.labels.map(
          (label, i) => html`<li class=${h === i ? 'active' : ''} @pointerenter=${() => (this.hover = i)} @pointerleave=${() => (this.hover = null)}>
            <span class="swatch" style="background:${SERIES_COLORS[i]}"></span><span class="name">${label}</span>
            <strong>${fmtValue(values[i], '')}</strong><span class="muted">${total > 0 ? Math.round((values[i] / total) * 100) : 0}%</span>
          </li>`
        )}
      </ul>
    </div>`;
  }

  private renderMeter() {
    const p = this.props;
    const value = p.value ?? 0;
    const max = p.max || 1;
    const ratio = value / max;
    const status = meterStatus(ratio);
    const word = ratio >= 1 ? 'Limit reached' : { good: 'Within limit', warning: 'Nearing limit', critical: 'Almost at limit' }[status];
    return html`<div class="meter" role="meter" aria-valuenow=${value} aria-valuemin="0" aria-valuemax=${max} aria-label=${this.describe()}>
      <div class="meter-figure"><strong>${fmtValue(value, '')}</strong><span class="muted">of ${fmtValue(max, this.unit)}</span></div>
      <div class="track"><div class="fill" style="width:${Math.min(100, ratio * 100)}%;background:${STATUS_COLORS[status]}"></div></div>
      <div class="meter-status"><span class="status-dot" style="background:${STATUS_COLORS[status]}"></span>${word}, ${Math.round(ratio * 100)}%</div>
    </div>`;
  }

  private renderTable() {
    const p = this.props;
    return html`<table class="data">
      <thead><tr><th></th>${p.series.map((s) => html`<th>${s.name}</th>`)}</tr></thead>
      <tbody>${p.labels.map((l, i) => html`<tr><th>${l}</th>${p.series.map((s) => html`<td>${fmtValue(s.values[i] ?? 0, this.unit)}</td>`)}</tr>`)}</tbody>
    </table>`;
  }

  render() {
    const p = this.props;
    if (!p?.chart) return nothing;
    const cartesian = p.chart !== 'meter' && !ROUND.has(p.chart);
    const legend =
      cartesian && p.series.length > 1
        ? html`<ul class="legend">${p.series.map((s, i) => html`<li><span class=${p.chart === 'line' ? 'swatch line' : 'swatch'} style="background:${SERIES_COLORS[i]}"></span>${s.name}</li>`)}</ul>`
        : nothing;
    const body = p.chart === 'meter' ? this.renderMeter() : ROUND.has(p.chart) ? this.renderRound() : this.renderCartesian();
    return html`
      ${this.heading ? html`<h4 class="title">${this.heading}</h4>` : nothing} ${legend}
      <div class="plot">${this.showTable && p.chart !== 'meter' ? this.renderTable() : body}</div>
      ${p.chart !== 'meter'
        ? html`<button type="button" class="toggle" @click=${() => (this.showTable = !this.showTable)}>${this.showTable ? 'Show chart' : 'Show data'}</button>`
        : nothing}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'now-chart-tile': NowChartTile;
  }
}
