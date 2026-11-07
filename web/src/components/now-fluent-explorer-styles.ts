// web/src/components/now-fluent-explorer-styles.ts
// Styles of <now-fluent-explorer> in the Otto look (ADR-019; ADR-024: CSS beside its component).
// The bundle picker is the shared .select-input (form-styles.ts).
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const fluentExplorerStyles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: var(--otto-canvas, #efece7);
      color: var(--now-text-primary, #0f172a);
      overflow: hidden;
    }

    /* The header blends into the canvas, as the Otto top bar. */
    .header-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 24px 36px 16px;
    }

    .title-group {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }

    .title-icon {
      padding: 4px 8px;
      border-radius: var(--now-radius-md, 10px);
      background: #e4e1db;
      color: #2b2d31;
      font-family: var(--now-font-mono, monospace);
      font-size: 12px;
      font-weight: 600;
    }

    .title-text {
      font-size: 24px;
      font-weight: 500;
      color: var(--now-text-primary, #0f172a);
    }

    .title-sub {
      font-size: 13px;
      color: var(--now-text-secondary, #475467);
      margin-top: 2px;
    }

    /* Warm chip, as Otto's "Learn more" (ADR-019). */
    .bundle-badge {
      font-size: 12px;
      font-weight: 500;
      padding: 3px 10px;
      background: #e4e1db;
      color: #2b2d31;
      border-radius: var(--now-radius-md, 10px);
      overflow-wrap: anywhere;
    }

    .actions-group {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .bundle-select {
      width: auto;
      max-width: 320px;
      padding: 7px 12px;
      font-size: 13px;
    }

    .bundle-list-error {
      font-size: 12.5px;
      color: #b42318;
    }

    .btn {
      position: relative;
      display: inline-flex;
      align-items: center;
      border-radius: var(--now-radius-pill, 9999px);
      cursor: pointer;
      border: 1px solid transparent;
    }

    .btn.icon-btn {
      width: 36px;
      height: 36px;
      padding: 0;
      justify-content: center;
      flex-shrink: 0;
    }

    .btn.icon-btn svg {
      width: 16px;
      height: 16px;
      fill: currentColor;
    }

    .btn-secondary {
      background: var(--now-bg-surface-0, #ffffff);
      border-color: var(--now-border-subtle, #e2e8f0);
      color: var(--now-text-primary, #0f172a);
    }

    .btn-secondary:hover {
      background: #f4f3f0;
      border-color: var(--now-border-medium, #cbd5e1);
    }

    .explorer-body {
      display: flex;
      flex: 1;
      gap: 24px;
      padding: 0 36px 24px;
      overflow: hidden;
    }

    /* Tables menu: a white card of rows, the chosen one dark (as the Settings menu). */
    .tables-sidebar {
      width: 260px;
      flex-shrink: 0;
      align-self: flex-start;
      max-height: 100%;
      box-sizing: border-box;
      background: var(--now-bg-surface-0, #ffffff);
      border-radius: var(--now-radius-lg, 16px);
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      padding: 8px;
      gap: 4px;
    }

    .sidebar-label {
      padding: 8px 12px 6px;
      font-size: 12.5px;
      font-weight: 600;
      color: var(--now-text-secondary, #475467);
    }

    .table-nav-btn {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 9px 12px;
      border-radius: var(--now-radius-md, 10px);
      border: none;
      background: transparent;
      color: var(--now-text-primary, #0f172a);
      cursor: pointer;
      text-align: left;
      font-family: inherit;
      transition: background-color 0.1s ease;
    }

    .table-nav-btn:hover {
      background: var(--otto-canvas-active, #e3dfd8);
    }

    .table-nav-btn.active {
      background: #1a1a1a;
      color: #ffffff;
    }

    .table-nav-name {
      font-size: 13.5px;
      font-weight: 600;
    }

    .table-nav-id {
      font-size: 11.5px;
      color: var(--now-text-muted, #64748b);
      font-family: var(--now-font-mono, monospace);
      overflow-wrap: anywhere;
    }

    .table-nav-btn:hover .table-nav-id {
      color: var(--now-text-secondary, #475467); /* 5.8:1 on #e3dfd8; muted is 3.6:1 */
    }

    .table-nav-btn.active .table-nav-id {
      color: #d0d0d0;
    }

    .table-col-count {
      font-size: 11.5px;
      padding: 2px 8px;
      background: #f4f3f0;
      border-radius: var(--now-radius-pill, 9999px);
      color: var(--now-text-secondary, #475467);
      font-weight: 600;
    }

    .table-nav-btn.active .table-col-count {
      background: #ffffff;
      color: #1a1a1a;
    }

    .schema-detail {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      gap: 16px;
    }

    .state-msg {
      padding: 40px;
      text-align: center;
      color: var(--now-text-secondary, #475467);
    }

    .state-error,
    .diff-error {
      color: #b42318;
    }

    .diff-error {
      padding: 12px;
    }

    .table-card {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid rgba(0, 0, 0, 0.05);
      border-radius: var(--now-radius-lg, 16px);
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
      padding: 24px;
    }

    .diff-card {
      border-left: 4px solid var(--now-color-accent-blue, #0284c7);
    }

    .table-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 16px;
      border-bottom: 1px solid #f4f3f0;
      padding-bottom: 12px;
    }

    .table-headline {
      font-size: 16px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
      overflow-wrap: anywhere;
    }

    .diff-body {
      margin-top: 8px;
      font-size: 13px;
      color: var(--now-text-secondary, #475467);
      overflow-wrap: anywhere;
    }

    .diff-ok {
      color: #15803d;
      font-weight: 600;
    }

    .table-identifier {
      font-size: 12.5px;
      color: var(--now-text-secondary, #475467);
      font-family: var(--now-font-mono, monospace);
      margin-top: 2px;
      overflow-wrap: anywhere;
    }

    .columns-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }

    .columns-table th {
      text-align: left;
      padding: 10px 14px;
      background: #f4f3f0;
      color: var(--now-text-secondary, #475467);
      font-size: 12.5px;
      font-weight: 600;
      white-space: nowrap;
    }

    .columns-table td {
      padding: 12px 14px;
      border-bottom: 1px solid #f4f3f0;
      color: var(--now-text-primary, #0f172a);
    }

    .col-name {
      font-family: var(--now-font-mono, monospace);
      font-weight: 600;
      color: var(--now-text-primary, #0f172a);
    }

    .col-ref {
      color: #1d4ed8;
    }

    .muted {
      color: var(--now-text-muted, #64748b);
    }

    .type-pill {
      font-size: 11.5px;
      padding: 2px 8px;
      border-radius: var(--now-radius-pill, 9999px);
      background: #f4f3f0;
      font-weight: 600;
      color: var(--now-text-secondary, #475467);
    }

    .type-pill.reference {
      background: #eff6ff;
      color: #1d4ed8;
    }

    .mandatory-pill {
      font-size: 11.5px;
      padding: 2px 8px;
      border-radius: var(--now-radius-pill, 9999px);
      background: #fef2f2;
      color: #b91c1c;
      font-weight: 600;
    }

    .source-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }

    .source-title {
      font-weight: 700;
      font-size: 14px;
      color: var(--now-text-primary, #0f172a);
    }

    .code-box {
      background: var(--now-text-primary, #0f172a);
      color: #f8fafc;
      border-radius: var(--now-radius-md, 10px);
      padding: 16px;
      font-family: var(--now-font-mono, monospace);
      font-size: 12.5px;
      line-height: 1.5;
      overflow-x: auto;
      position: relative;
    }

    .code-pre {
      margin: 0;
    }

    .copy-btn {
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(255, 255, 255, 0.1);
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: #ffffff;
      padding: 0;
      width: 32px;
      height: 32px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: var(--now-radius-pill, 9999px);
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
        padding: 16px 24px 12px;
      }

      .title-group {
        flex-wrap: wrap;
      }

      .actions-group {
        flex-wrap: wrap;
        max-width: 100%;
      }

      .bundle-select {
        max-width: 100%;
      }

      .explorer-body {
        flex-direction: column;
        overflow-y: auto;
        gap: 12px;
        padding: 0 24px 16px;
      }

      .tables-sidebar {
        width: auto;
        max-height: none;
        align-self: stretch;
        flex-direction: row;
        align-items: center;
        overflow-x: auto;
        overflow-y: hidden;
        scrollbar-width: none;
        padding: 6px;
      }

      .sidebar-label {
        flex-shrink: 0;
        padding: 0 8px;
      }

      .table-nav-btn {
        flex-shrink: 0;
      }

      .schema-detail {
        overflow: visible;
        gap: 12px;
      }

      .table-card {
        overflow-x: auto;
      }
    }

    /* Phones (ADR-030): 12px gutters, 40px touch targets, a 16px picker so iOS does not zoom. */
    @media (max-width: 768px), (max-height: 500px) {
      .header-bar {
        padding: 12px;
      }

      .title-text {
        font-size: 20px;
      }

      .explorer-body {
        padding: 0 12px 12px;
      }

      .table-card {
        padding: 16px;
      }

      /* A row above the code for the 40px copy button, so it never covers a line. */
      .code-box {
        padding-top: 58px;
      }

      .btn.icon-btn,
      .copy-btn {
        width: 40px;
        height: 40px;
      }

      .table-nav-btn {
        min-height: 40px;
      }

      .bundle-select {
        font-size: 16px;
      }

      .state-msg {
        padding: 32px 12px;
      }
    }
`;
