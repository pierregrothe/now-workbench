// web/src/components/now-fluent-explorer-styles.ts
// Styles of <now-fluent-explorer> (ADR-024: CSS lives beside its component).
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const fluentExplorerStyles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: var(--now-bg-canvas, #f8fafc);
      overflow: hidden;
      font-family: inherit;
    }

    .header-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 24px;
      background: var(--now-bg-surface-0, #ffffff);
      border-bottom: 1px solid var(--now-border-subtle, #e2e8f0);
    }

    .title-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .title-icon {
      font-size: 20px;
    }

    .title-text {
      font-size: 16px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
    }

    .bundle-badge {
      font-size: 11.5px;
      padding: 3px 10px;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      color: #1d4ed8;
      border-radius: 9999px;
      font-weight: 600;
    }

    .actions-group {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .bundle-list-error {
      font-size: 12.5px;
      color: #b42318;
    }

    .btn {
      position: relative;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid transparent;
      transition: all 0.15s ease;
    }

    .btn.icon-btn {
      width: 32px;
      height: 32px;
      padding: 0;
      justify-content: center;
      border-radius: 6px;
    }

    .btn.icon-btn svg {
      width: 16px;
      height: 16px;
      fill: currentColor;
    }

    .btn-secondary {
      background: var(--now-bg-surface-0, #ffffff);
      border-color: var(--now-border-subtle, #cbd5e1);
      color: var(--now-text-primary, #0f172a);
    }

    .btn-secondary:hover {
      background: var(--now-bg-surface-1, #f8fafc);
      border-color: #94a3b8;
    }

    .explorer-body {
      display: flex;
      flex: 1;
      overflow: hidden;
    }

    .tables-sidebar {
      width: 280px;
      background: var(--now-bg-surface-0, #ffffff);
      border-right: 1px solid var(--now-border-subtle, #e2e8f0);
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      padding: 12px;
      gap: 6px;
    }

    .table-nav-btn {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      border-radius: 8px;
      border: 1px solid transparent;
      background: transparent;
      cursor: pointer;
      text-align: left;
      font-family: inherit;
      transition: background-color 0.1s ease;
    }

    .table-nav-btn:hover {
      background: var(--now-bg-surface-1, #f1f5f9);
    }

    .table-nav-btn.active {
      background: #f0fdf4;
      border-color: #bbf7d0;
    }

    .table-nav-name {
      font-size: 13px;
      font-weight: 600;
      color: var(--now-text-primary, #0f172a);
    }

    .table-col-count {
      font-size: 11px;
      padding: 2px 7px;
      background: var(--now-bg-surface-2, #e2e8f0);
      border-radius: 12px;
      color: var(--now-text-primary, #475569);
      font-weight: 600;
    }

    .table-nav-btn.active .table-col-count {
      background: var(--now-color-brand-green, #293e40);
      color: #ffffff;
    }

    .schema-detail {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      padding: 24px;
      gap: 20px;
    }

    .table-card {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: 10px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
      padding: 20px;
    }

    .table-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
      border-bottom: 1px solid #f1f5f9;
      padding-bottom: 12px;
    }

    .table-headline {
      font-size: 18px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
    }

    .table-identifier {
      font-size: 12.5px;
      color: var(--now-text-secondary, #64748b);
      font-family: monospace;
      margin-top: 2px;
    }

    .columns-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }

    .columns-table th {
      text-align: left;
      padding: 10px 14px;
      background: var(--now-bg-surface-1, #f8fafc);
      color: var(--now-text-secondary, #64748b);
      font-size: 11.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      border-bottom: 1px solid var(--now-border-subtle, #e2e8f0);
    }

    .columns-table td {
      padding: 12px 14px;
      border-bottom: 1px solid #f1f5f9;
      color: var(--now-text-primary, #0f172a);
    }

    .col-name {
      font-family: monospace;
      font-weight: 600;
      color: var(--now-text-primary, #0f172a);
    }

    .type-pill {
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 4px;
      background: var(--now-bg-surface-1, #f1f5f9);
      font-weight: 600;
      color: var(--now-text-secondary, #334155);
    }

    .type-pill.reference {
      background: #eff6ff;
      color: #1d4ed8;
      border: 1px solid #bfdbfe;
    }

    .mandatory-pill {
      font-size: 11px;
      padding: 2px 7px;
      border-radius: 4px;
      background: #fef2f2;
      color: #b91c1c;
      border: 1px solid #fecaca;
      font-weight: 600;
    }

    .code-box {
      background: #1e293b;
      color: #e2e8f0;
      border-radius: 8px;
      padding: 16px;
      font-family: monospace;
      font-size: 12.5px;
      line-height: 1.5;
      overflow-x: auto;
      position: relative;
    }

    .copy-btn {
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: #ffffff;
      padding: 0;
      width: 28px;
      height: 28px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
      cursor: pointer;
    }

    .copy-btn svg {
      width: 15px;
      height: 15px;
      fill: currentColor;
    }

    .copy-btn:hover {
      background: rgba(255, 255, 255, 0.2);
    }
  
    /* Narrow screens (ADR-030): tables become a scrolling strip above the schema. */
    @media (max-width: 900px) {
      .header-bar {
        flex-wrap: wrap;
        gap: 10px;
        padding: 12px;
      }

      .title-group {
        flex-wrap: wrap;
        min-width: 0;
      }

      .actions-group {
        flex-wrap: wrap;
        max-width: 100%;
      }

      .actions-group select {
        max-width: 100%;
      }

      .explorer-body {
        flex-direction: column;
        overflow-y: auto;
      }

      .tables-sidebar {
        width: auto;
        flex-direction: row;
        flex-shrink: 0;
        overflow-x: auto;
        overflow-y: hidden;
        border-right: none;
        border-bottom: 1px solid var(--now-border-subtle, #e2e8f0);
      }

      .table-nav-btn {
        flex-shrink: 0;
        gap: 10px;
      }

      .schema-detail {
        overflow: visible;
        padding: 12px;
        gap: 12px;
      }

      .table-card {
        overflow-x: auto;
      }
    }
`;
