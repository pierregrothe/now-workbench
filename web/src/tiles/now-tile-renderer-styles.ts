// web/src/tiles/now-tile-renderer-styles.ts
// Styles of <now-tile-renderer> (ADR-024: CSS lives beside its component).
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const tileRendererStyles = css`
    :host { display: block; font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .gen-tile { background: var(--now-bg-surface-0, #ffffff); border: 1px solid rgba(0,0,0,0.05); border-radius: 16px; padding: 18px 20px; display: flex; flex-direction: column; gap: 10px; box-shadow: 0 1px 2px rgba(0,0,0,0.04); transition: all 0.15s ease; text-align: left; }
    .gen-tile:hover { box-shadow: 0 4px 18px rgba(0,0,0,0.06); }
    .open-btn { border: none; background: transparent; cursor: pointer; font-size: 15px; line-height: 1; color: var(--now-text-secondary, #4b5563); padding: 2px 4px; border-radius: 6px; }
    .open-btn:hover { background: rgba(0,0,0,0.06); }
    .gen-tile.kpi { }
    .gen-kpi-top { display: flex; align-items: center; justify-content: space-between; }
    .gen-kpi-icon { width: 32px; height: 32px; border-radius: 8px; background: #dcfce7; color: #15803d; display: flex; align-items: center; justify-content: center; }
    .gen-kpi-icon svg { width: 17px; height: 17px; stroke: currentColor; stroke-width: 2; fill: none; }
    .gen-kpi-number { font-size: 34px; font-weight: 800; color: var(--now-text-primary, #0f172a); line-height: 1; letter-spacing: -0.02em; margin-top: 4px; }
    .gen-kpi-label { font-size: 13.5px; font-weight: 700; color: var(--now-text-primary, #0f172a); }
    .gen-kpi-sub { font-size: 11.5px; color: var(--now-text-secondary, #475467); }
    .gen-card-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
    .gen-card-title { font-size: 14.5px; font-weight: 700; color: var(--now-text-primary, #0f172a); margin: 0; display: flex; align-items: center; gap: 6px; }
    .gen-card-url { font-size: 11.5px; font-family: monospace; color: var(--now-text-secondary, #475467); background: var(--now-bg-surface-1, #f8fafc); padding: 5px 10px; border-radius: 6px; border: 1px solid var(--now-border-subtle, #f1f5f9); word-break: break-all; }
    .gen-card-meta-row { display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: var(--now-text-secondary, #475467); }
    .gen-tile.alert-tile { background: #fef2f2; border-color: #fee2e2; border-left: 4px solid #dc2626; }
    .gen-alert-title { font-size: 14px; font-weight: 700; color: #991b1b; margin: 0; }
    .gen-alert-desc { font-size: 12.5px; color: #7f1d1d; line-height: 1.45; margin: 0; }
    .gen-tile.rich { background: var(--now-bg-surface-0, #ffffff); }
    .gen-rich-title { font-size: 13.5px; font-weight: 700; color: var(--now-text-primary, #0f172a); margin: 0; }
    .gen-rich-body { font-size: 12.5px; color: var(--now-text-secondary, #475467); line-height: 1.5; white-space: pre-wrap; }
    .gen-tile.table-tile { background: var(--now-bg-surface-0, #ffffff); border-left: 4px solid #2563eb; overflow-x: auto; }
    .gen-table-title { font-size: 13.5px; font-weight: 700; color: var(--now-text-primary, #0f172a); margin: 0; }
    .gen-data-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 4px; }
    .gen-data-table th { text-align: left; padding: 6px 10px; background: var(--now-bg-surface-1, #f8fafc); color: #64748b; font-weight: 600; border-bottom: 1px solid #e2e8f0; font-size: 11px; text-transform: uppercase; }
    .gen-data-table td { padding: 6px 10px; border-bottom: 1px solid #f1f5f9; color: #0f172a; }
    .gen-actions-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 6px; }
    .ct-action-btn { padding: 5px 12px; border-radius: 6px; font-size: 11.5px; font-weight: 600; border: 1px solid #cbd5e1; background: #ffffff; color: #334155; cursor: pointer; transition: all 0.15s ease; }
    .ct-action-btn:hover { background: #f1f5f9; border-color: #94a3b8; }
    .ct-action-btn.primary { background: var(--now-color-primary, #032d42); color: #ffffff; border-color: var(--now-color-primary, #032d42); }
    .ct-tag { display: inline-flex; align-items: center; padding: 2px 7px; border-radius: 4px; font-size: 10.5px; font-weight: 600; text-transform: uppercase; }
    .ct-tag.high { background: #dcfce7; color: #15803d; }
    .ct-tag.critical { background: #fee2e2; color: #b91c1c; }
    .ct-tag.medium { background: #fef3c7; color: #b45309; }
    .ct-tag.low { background: #f1f5f9; color: #475569; }

    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; }
    .kpi-item { border: 1px solid var(--now-border-subtle, #e2e8f0); border-radius: 12px; padding: 10px 12px; display: flex; flex-direction: column; gap: 2px; }
    .kpi-value { font-size: 22px; font-weight: 800; color: var(--now-text-primary, #0f172a); line-height: 1.1; }
    .kpi-label { font-size: 11.5px; font-weight: 600; color: var(--now-text-secondary, #475467); text-transform: uppercase; letter-spacing: 0.03em; }
    .kpi-hint { font-size: 11px; color: var(--now-text-secondary, #64748b); }
    .kpi-item.good .kpi-value { color: #15803d; }
    .kpi-item.warn .kpi-value { color: #b45309; }
    .kpi-item.bad .kpi-value { color: #b91c1c; }
    .steps-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
    .step { display: grid; grid-template-columns: 20px 1fr; gap: 8px; align-items: start; font-size: 12.5px; }
    .step-dot { width: 18px; height: 18px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; border: 1.5px solid #cbd5e1; color: #64748b; }
    .step.done .step-dot { background: #dcfce7; border-color: #16a34a; color: #15803d; }
    .step.running .step-dot { background: #dbeafe; border-color: #2563eb; color: #1d4ed8; }
    .step.failed .step-dot { background: #fee2e2; border-color: #dc2626; color: #b91c1c; }
    .step.skipped { opacity: 0.55; }
    .step-label { font-weight: 600; color: var(--now-text-primary, #0f172a); }
    .step-detail { color: var(--now-text-secondary, #475467); font-size: 11.5px; }
    .compare-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
    .compare-col { background: var(--now-bg-surface-1, #f8fafc); border-radius: 10px; padding: 10px 12px; }
    .compare-col h5 { margin: 0 0 6px; font-size: 12.5px; color: var(--now-text-primary, #0f172a); }
    .compare-col ul { margin: 0; padding-left: 16px; font-size: 12px; color: var(--now-text-secondary, #475467); display: flex; flex-direction: column; gap: 3px; }
    .gen-tile.callout { border-left: 4px solid #2563eb; background: #eff6ff; }
    .gen-tile.callout.success { border-left-color: #16a34a; background: #f0fdf4; }
    .gen-tile.callout.warning { border-left-color: #d97706; background: #fffbeb; }
    .gen-tile.callout.danger { border-left-color: #dc2626; background: #fef2f2; }
  `;
