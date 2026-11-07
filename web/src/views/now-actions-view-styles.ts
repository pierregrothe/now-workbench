// web/src/views/now-actions-view-styles.ts
// Styles of <now-actions-view> (ADR-024: CSS lives beside its component).
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const actionsViewStyles = css`
  .actions-layout {
    display: grid;
    grid-template-columns: 300px minmax(0, 1fr);
    gap: 20px;
    padding: 20px 36px 40px;
    min-height: 0;
    flex: 1;
    overflow: hidden;
  }
  .catalog {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 0;
    overflow-y: auto;
  }
  .search {
    width: 100%;
    box-sizing: border-box;
    padding: 9px 12px;
    border-radius: 10px;
    border: 1px solid var(--now-border-subtle, #d1d5db);
    font: inherit;
    font-size: 13px;
  }
  .category {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--now-text-secondary, #6b7280);
    margin: 10px 4px 2px;
  }
  .action-item {
    text-align: left;
    border: none;
    background: transparent;
    padding: 7px 10px;
    border-radius: 8px;
    font: inherit;
    font-size: 13px;
    color: var(--now-text-primary, #111827);
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    gap: 8px;
  }
  .action-item:hover {
    background: rgba(0, 0, 0, 0.05);
  }
  .action-item.active {
    background: #111827;
    color: #fff;
  }
  .confirm-tag {
    font-size: 10px;
    opacity: 0.7;
  }
  .panel {
    background: var(--now-bg-surface-0, #fff);
    border-radius: 16px;
    padding: 22px 24px;
    overflow-y: auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .panel h2 {
    margin: 0;
    font-size: 18px;
  }
  .desc {
    margin: 0;
    font-size: 13px;
    color: var(--now-text-secondary, #4b5563);
    line-height: 1.5;
  }
  .fields {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 12px;
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: 5px;
    font-size: 12px;
    font-weight: 600;
    color: var(--now-text-secondary, #374151);
  }
  .field input[type='text'],
  .field input[type='number'],
  .field select,
  .field textarea {
    font: inherit;
    font-size: 13px;
    font-weight: 400;
    padding: 8px 10px;
    border-radius: 8px;
    border: 1px solid var(--now-border-subtle, #d1d5db);
    background: var(--now-bg-surface-1, #f9fafb);
  }
  .field textarea {
    min-height: 70px;
    font-family: monospace;
  }
  .field .hint {
    font-weight: 400;
    color: var(--now-text-secondary, #6b7280);
  }
  .check {
    flex-direction: row;
    align-items: center;
    gap: 8px;
  }
  .run-row {
    display: flex;
    gap: 10px;
    align-items: center;
  }
  .btn {
    border: 1px solid #111827;
    background: #111827;
    color: #fff;
    border-radius: 999px;
    padding: 8px 18px;
    font: inherit;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
  }
  .btn.secondary {
    background: #fff;
    color: #111827;
  }
  .btn:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .result {
    border-radius: 12px;
    padding: 12px 14px;
    font-size: 13px;
    background: #f0fdf4;
    color: #14532d;
  }
  .result.error {
    background: #fef2f2;
    color: #991b1b;
  }
  .result.pending {
    background: #fffbeb;
    color: #78350f;
  }
  .tiles {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 14px;
  }
  .tiles > now-tile-renderer {
    grid-column: span var(--tile-span, 6);
    min-width: 0;
  }
  .empty {
    color: var(--now-text-secondary, #6b7280);
    font-size: 13px;
  }
  @media (max-width: 900px) {
    /* One column that scrolls as a whole; the chosen action's form comes first (ADR-030). */
    .actions-layout {
      grid-template-columns: minmax(0, 1fr);
      overflow-y: auto;
      padding: 12px 12px 24px;
    }
    .catalog {
      overflow: visible;
    }
    .actions-layout.picked .panel {
      order: -1;
    }
    .actions-layout:not(.picked) .panel {
      display: none;
    }
    .action-item {
      min-height: 40px;
      align-items: center;
    }
    .tiles > now-tile-renderer {
      grid-column: 1 / -1;
    }
  }
`;
