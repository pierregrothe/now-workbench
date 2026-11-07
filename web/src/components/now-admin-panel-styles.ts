// web/src/components/now-admin-panel-styles.ts
// Styles of <now-admin-panel>: page layout and the instance table (ADR-024).
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const adminPanelStyles = css`
    :host {
      display: flex;
      flex-direction: column;
      width: 100%;
      height: 100%;
      background-color: var(--now-bg-canvas, #ffffff);
      color: var(--now-text-primary, #16181d);
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      overflow-y: auto;
    }

    .instances-scroll {
      flex: 1;
      padding: 32px 36px 48px 36px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .instances-container {
      width: 100%;
      max-width: 1020px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    /* Instance Table */
    .table-wrapper {
      border: 1px solid var(--now-border-subtle, #e5e7eb);
      border-radius: 12px;
      overflow: hidden;
    }

    .instances-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      text-align: left;
    }

    .instances-table th {
      background: var(--now-bg-surface-1, #f9fafb);
      padding: 12px 16px;
      font-size: 11.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--now-text-secondary, #4b5563);
      border-bottom: 1px solid var(--now-border-subtle, #e5e7eb);
    }

    .instances-table td.empty-state {
      padding: 28px 16px;
      text-align: center;
      color: var(--now-text-secondary, #6b7280);
      font-style: italic;
    }

    .instances-table td {
      padding: 14px 16px;
      border-bottom: 1px solid var(--now-border-subtle, #f1f2f0);
      color: var(--now-text-primary, #1f2937);
      vertical-align: middle;
    }

    .instances-table tr:last-child td {
      border-bottom: none;
    }

    .instances-table tr:hover td {
      background: var(--now-bg-surface-1, #fcfcfb);
    }

    .instance-name-col {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .inst-title {
      font-weight: 600;
      color: var(--now-text-primary, #0f172a);
    }

    .inst-url-sub {
      font-family: "JetBrains Mono", monospace;
      font-size: 11.5px;
      color: var(--now-text-secondary, #64748b);
    }

    /* Table row badges (environment purpose, datacenter) */
    .env-badge {
      display: inline-block;
      margin-left: 6px;
      padding: 1px 7px;
      border-radius: 999px;
      font-size: 10.5px;
      font-weight: 700;
      background: var(--now-bg-surface-0, #f1f5f9);
      color: var(--now-text-secondary, #475467);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
    }

    .env-badge.prod {
      background: #fef2f2;
      color: #b42318;
      border-color: #fecaca;
    }

    .row-dc {
      display: block;
      font-size: 11px;
      color: var(--now-text-secondary, #6b7280);
    }
  `;
