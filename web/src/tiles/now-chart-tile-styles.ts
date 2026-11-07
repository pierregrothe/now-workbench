// web/src/tiles/now-chart-tile-styles.ts
// Styles of <now-chart-tile> (ADR-024: CSS lives beside its component; ADR-027 mark specs).
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const chartTileStyles = css`
  :host {
    display: block;
    position: relative;
    min-width: 0;
    font-family: inherit;
    color: var(--now-text-primary, #0b0b0b);
  }
  .title {
    margin: 0 0 6px;
    font-size: 13px;
    font-weight: 700;
  }
  .plot {
    position: relative;
  }
  svg {
    display: block;
    overflow: visible;
  }
  .grid {
    stroke: #e1e0d9;
    stroke-width: 1;
  }
  .baseline {
    stroke: #c3c2b7;
    stroke-width: 1;
  }
  .tick {
    font-size: 11px;
    fill: #898781;
    font-variant-numeric: tabular-nums;
  }
  .line {
    fill: none;
    stroke-width: 2;
    stroke-linejoin: round;
    stroke-linecap: round;
  }
  .dot {
    stroke: var(--now-bg-surface-0, #fff);
    stroke-width: 2;
  }
  .end-label {
    font-size: 11px;
    font-weight: 600;
    fill: #52514e;
  }
  .crosshair {
    stroke: #898781;
    stroke-width: 1;
  }
  .band-hover {
    fill: rgba(11, 11, 11, 0.05);
    pointer-events: none;
  }
  .slice {
    stroke: var(--now-bg-surface-0, #fff);
    stroke-width: 2;
    transition: opacity 120ms;
  }
  svg:hover .slice:not(.lift) {
    opacity: 0.55;
  }
  .center-value {
    font-size: 20px;
    font-weight: 700;
    fill: #0b0b0b;
  }
  .center-label {
    font-size: 11px;
    fill: #52514e;
  }
  .round {
    display: flex;
    align-items: center;
    gap: 18px;
    flex-wrap: wrap;
  }
  .legend {
    list-style: none;
    margin: 0 0 8px;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 6px 14px;
    font-size: 12px;
    color: #52514e;
  }
  .legend li {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .legend.vertical {
    flex-direction: column;
    flex: 1;
    min-width: 140px;
    gap: 4px;
  }
  .legend.vertical li {
    border-radius: 6px;
    padding: 2px 4px;
  }
  .legend.vertical li.active {
    background: rgba(11, 11, 11, 0.05);
  }
  .legend .name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .legend strong {
    color: #0b0b0b;
    font-variant-numeric: tabular-nums;
  }
  .swatch {
    width: 10px;
    height: 10px;
    border-radius: 3px;
    flex-shrink: 0;
  }
  .swatch.line {
    height: 2px;
    width: 14px;
    border-radius: 1px;
  }
  .muted {
    color: #898781;
    font-size: 11px;
  }
  .tooltip {
    position: absolute;
    top: 4px;
    min-width: 140px;
    max-width: 200px;
    background: #fff;
    border: 1px solid rgba(11, 11, 11, 0.1);
    border-radius: 8px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
    padding: 8px 10px;
    font-size: 12px;
    pointer-events: none;
  }
  .tip-head {
    color: #52514e;
    margin-bottom: 4px;
  }
  .tip-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .tip-row strong {
    font-variant-numeric: tabular-nums;
  }
  .key {
    width: 12px;
    height: 2px;
    border-radius: 1px;
  }
  .meter {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .meter-figure {
    display: flex;
    align-items: baseline;
    gap: 6px;
  }
  .meter-figure strong {
    font-size: 22px;
  }
  .track {
    height: 10px;
    border-radius: 5px;
    background: #f0efec;
    overflow: hidden;
  }
  .fill {
    height: 100%;
    border-radius: 5px;
  }
  .meter-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #52514e;
  }
  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }
  .toggle {
    margin-top: 6px;
    border: none;
    background: none;
    padding: 2px 0;
    font: inherit;
    font-size: 11px;
    color: #52514e;
    text-decoration: underline;
    cursor: pointer;
  }
  table.data {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }
  table.data th,
  table.data td {
    text-align: right;
    padding: 4px 6px;
    border-bottom: 1px solid #e1e0d9;
  }
  table.data th:first-child {
    text-align: left;
  }
  table.data thead th {
    color: #52514e;
    font-weight: 600;
  }
`;
