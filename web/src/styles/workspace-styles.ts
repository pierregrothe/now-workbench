// web/src/styles/workspace-styles.ts
// Shared ServiceNow Lux design tokens & styles for views and tiles.
// Author: Pierre Grothe
// Date: 2026-10-31

import { css } from 'lit';

export const workspaceStyles = css`
  :host {
    display: flex;
    flex-direction: column;
    height: 100%;
    background-color: var(--now-bg-canvas, #ffffff);
    color: var(--now-text-primary, #16181d);
    font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }

  .top-utility-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 36px;
    border-bottom: 1px solid var(--now-border-subtle, #f0f0ee);
    background: var(--now-bg-surface-0, #ffffff);
    flex-shrink: 0;
  }

  .workspace-breadcrumb {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 500;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: var(--now-color-status-success, #38a169);
    display: inline-block;
  }

  .utility-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .instance-picker-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--now-bg-surface-2, #f3f4f6);
    padding: 4px 10px;
    border-radius: 9999px;
    border: 1px solid var(--now-border-subtle, #e5e7eb);
    font-size: 11px;
  }

  .instance-picker-label {
    color: var(--now-text-secondary, #6b7280);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .instance-picker-select {
    border: none;
    background: transparent;
    font-size: 12px;
    font-weight: 600;
    color: var(--now-text-primary, #16181d);
    outline: none;
    cursor: pointer;
  }

  .pill-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border-radius: 9999px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid var(--now-border-subtle, #e5e7eb);
    background: var(--now-bg-surface-0, #ffffff);
    color: var(--now-text-primary, #16181d);
    transition: all 0.15s ease;
  }

  .pill-btn:hover {
    background: var(--now-bg-surface-1, #f9fafb);
  }

  .pill-btn.primary {
    background: var(--now-color-primary, #032d42);
    color: #ffffff;
    border-color: var(--now-color-primary, #032d42);
  }

  .pill-btn.primary:hover {
    background: #043b57;
  }

  .pill-btn.icon-btn {
    padding: 6px 10px;
  }

  .pill-btn svg {
    width: 14px;
    height: 14px;
    fill: currentColor;
  }

  .scroll-canvas {
    flex: 1;
    overflow-y: auto;
    padding: 24px 36px;
    background: var(--now-bg-surface-1, #f8fafc);
  }

  .canvas-container {
    max-width: 1200px;
    margin: 0 auto;
  }

  .section-title {
    font-size: 18px;
    font-weight: 700;
    margin: 0 0 16px 0;
    color: var(--now-text-primary, #16181d);
  }

  .section-subtitle {
    font-size: 13px;
    color: var(--now-text-secondary, #6b7280);
    margin: -10px 0 20px 0;
  }

  .card {
    background: var(--now-bg-surface-0, #ffffff);
    border: 1px solid var(--now-border-subtle, #e5e7eb);
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  }

  .badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
  }

  .badge.success {
    background: #ecfdf5;
    color: #047857;
  }

  .badge.warning {
    background: #fffbeb;
    color: #b45309;
  }

  .badge.error {
    background: #fef2f2;
    color: #b91c1c;
  }

  .badge.info {
    background: #eff6ff;
    color: #1d4ed8;
  }
`;
