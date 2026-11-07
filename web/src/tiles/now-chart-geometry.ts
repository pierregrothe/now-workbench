// web/src/tiles/now-chart-geometry.ts
// Pure helpers for <now-chart-tile>: palette, scales, number formats and SVG paths (ADR-027).
// Author: Pierre Grothe
// Date: 2026-11-07

/** Categorical slots in fixed order (validated: adjacent CVD dE >= 9.1 on white); never cycled. */
export const SERIES_COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948'];
/** Status colors, reserved for the meter and always paired with a label. */
export const STATUS_COLORS = { good: '#0ca30c', warning: '#fab219', critical: '#d03b3b' };

export interface ChartSeries {
  name: string;
  values: number[];
}

export interface ChartProps {
  chart: 'line' | 'area' | 'bar' | 'pie' | 'donut' | 'meter';
  labels: string[];
  series: ChartSeries[];
  unit?: string;
  stacked?: boolean;
  value?: number | null;
  max?: number | null;
}

const compact = new Intl.NumberFormat(undefined, { notation: 'compact', maximumFractionDigits: 1 });
const exact = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 });

/** 1234 -> '1.2K' for axes; full precision for tooltips and the table. */
export const fmtAxis = (v: number): string => compact.format(v);
export const fmtValue = (v: number, unit = ''): string => `${exact.format(v)}${unit ? ` ${unit}` : ''}`;

/** A round upper bound and the ticks up to it (0 included), about four steps. */
export function niceTicks(maxValue: number): number[] {
  if (!(maxValue > 0)) return [0, 1];
  const raw = maxValue / 4;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? 10 * mag;
  const ticks: number[] = [];
  for (let t = 0; t < maxValue + step * 0.999; t += step) ticks.push(Number(t.toPrecision(12)));
  return ticks;
}

/** Largest value the value axis must hold: the tallest stack, or the largest point. */
export function valueMax(p: ChartProps): number {
  const n = p.labels.length;
  if (p.chart === 'bar' && p.stacked) {
    let top = 0;
    for (let i = 0; i < n; i++) top = Math.max(top, p.series.reduce((sum, s) => sum + Math.max(0, s.values[i] ?? 0), 0));
    return top;
  }
  return Math.max(0, ...p.series.flatMap((s) => s.values));
}

/** Indexes of at most `count` evenly spaced x labels, first and last included. */
export function labelIndexes(n: number, count: number): number[] {
  if (n <= count) return [...Array(n).keys()];
  const step = (n - 1) / (count - 1);
  return [...new Set([...Array(count).keys()].map((i) => Math.round(i * step)))];
}

/** A column path with a 4px rounded data end and a square baseline end. */
export function columnPath(x: number, y: number, w: number, h: number, rounded: boolean): string {
  if (h <= 0) return '';
  const r = rounded ? Math.min(4, w / 2, h) : 0;
  return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
}

/** A pie or donut slice between two angles (radians, 0 = 12 o'clock, clockwise). */
export function slicePath(cx: number, cy: number, r: number, inner: number, a0: number, a1: number): string {
  const pt = (rad: number, a: number) => `${cx + rad * Math.sin(a)},${cy - rad * Math.cos(a)}`;
  const sweep = a1 - a0;
  if (sweep >= Math.PI * 2 - 1e-6) {
    // A single full slice: two half arcs, since one arc cannot close on itself.
    const ring = inner > 0 ? `M${pt(inner, 0)}A${inner},${inner} 0 1 0 ${pt(inner, Math.PI)}A${inner},${inner} 0 1 0 ${pt(inner, 0)}Z` : '';
    return `M${pt(r, 0)}A${r},${r} 0 1 1 ${pt(r, Math.PI)}A${r},${r} 0 1 1 ${pt(r, 0)}Z${ring}`;
  }
  const large = sweep > Math.PI ? 1 : 0;
  if (inner <= 0) return `M${cx},${cy}L${pt(r, a0)}A${r},${r} 0 ${large} 1 ${pt(r, a1)}Z`;
  return `M${pt(r, a0)}A${r},${r} 0 ${large} 1 ${pt(r, a1)}L${pt(inner, a1)}A${inner},${inner} 0 ${large} 0 ${pt(inner, a0)}Z`;
}

/** Points of a polyline as an SVG path. */
const linePath = (pts: [number, number][]): string => pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x},${y}`).join('');

/**
 * A smooth path through the points: cubic Beziers with monotone (Fritsch-Carlson) tangents.
 * Unlike a plain spline it never overshoots, so a curve between 5 and 0 cannot dip below zero
 * or peak above its data: the smoothing changes the look, never the values.
 */
export function smoothPath(pts: [number, number][]): string {
  const n = pts.length;
  if (n < 3) return linePath(pts);
  const dx = pts.slice(1).map(([x], i) => x - pts[i][0]);
  const m = pts.slice(1).map(([, y], i) => (y - pts[i][1]) / (dx[i] || 1));
  const t = pts.map((_, i) => {
    if (i === 0) return m[0];
    if (i === n - 1) return m[n - 2];
    const [a, b] = [m[i - 1], m[i]];
    if (a * b <= 0) return 0; // A peak, trough or flat run stays exactly at its point.
    return (3 * (dx[i - 1] + dx[i])) / ((2 * dx[i] + dx[i - 1]) / a + (dx[i] + 2 * dx[i - 1]) / b);
  });
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < n - 1; i++) {
    const h = dx[i] / 3;
    d += `C${pts[i][0] + h},${pts[i][1] + t[i] * h} ${pts[i + 1][0] - h},${pts[i + 1][1] - t[i + 1] * h} ${pts[i + 1][0]},${pts[i + 1][1]}`;
  }
  return d;
}

/** Meter status by share of the limit: under 70% good, under 90% warning, else critical. */
export function meterStatus(ratio: number): keyof typeof STATUS_COLORS {
  if (ratio < 0.7) return 'good';
  if (ratio < 0.9) return 'warning';
  return 'critical';
}
