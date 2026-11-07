// web/src/components/now-workbench-settings-styles.ts
// Styles of <now-workbench-settings> (ADR-024: CSS lives beside its component).
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const workbenchSettingsStyles = css`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: var(--otto-canvas, #efece7);
      color: var(--now-text-primary, #16181d);
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .top-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 36px;
      border-bottom: 1px solid var(--now-border-subtle, #f0f0ee);
      background: transparent;
      flex-shrink: 0;
    }

    .title-group {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .title-group h1 {
      font-size: 20px;
      font-weight: 700;
      color: var(--now-text-primary, #0b0f19);
      margin: 0;
      letter-spacing: -0.015em;
    }

    .prefs-layout {
      flex: 1;
      min-height: 0;
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: 8px;
      padding: 24px 36px 0;
      max-width: 1240px;
      width: 100%;
      margin: 0 auto;
      box-sizing: border-box;
    }

    .pref-nav {
      display: flex;
      flex-direction: column;
      gap: 4px;
      align-self: start;
      background: var(--now-bg-surface-0, #ffffff);
      border-radius: 16px;
      padding: 8px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    }

    .pref-nav-item {
      text-align: left;
      border: none;
      background: transparent;
      font: inherit;
      font-size: 13.5px;
      padding: 9px 12px;
      border-radius: 10px;
      cursor: pointer;
      color: var(--now-text-primary, #16181d);
    }

    .pref-nav-item:hover {
      background: var(--otto-canvas-active, #e3dfd8);
    }

    .pref-nav-item.active {
      background: #1a1a1a;
      color: #ffffff;
    }

    .pref-content {
      min-width: 0;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
    }

    .section-card[hidden] {
      display: none;
    }

    .scroll-body {
      flex: 1;
      overflow-y: auto;
      padding: 28px 36px 40px 36px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .settings-container {
      width: 100%;
      max-width: 980px;
      display: flex;
      flex-direction: column;
      gap: 22px;
    }

    .section-card {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e6e7e4);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 4px 18px var(--now-shadow-soft, rgba(0, 0, 0, 0.025));
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .section-card.featured {
      border-color: var(--now-border-subtle, #b8e2b0);
      background: linear-gradient(180deg, var(--now-color-brand-green-subtle, rgba(98, 216, 78, 0.08)) 0%, var(--now-bg-surface-0, #ffffff) 100%);
    }

    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid var(--now-border-subtle, #f2f2f0);
      padding-bottom: 14px;
    }

    .section-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--now-text-primary, #0b0f19);
      margin: 0;
    }

    .section-desc {
      font-size: 12.5px;
      color: var(--now-text-secondary, #6b7280);
      margin: 3px 0 0 0;
    }

    .key-status-pill {
      font-size: 11.5px;
      font-weight: 600;
      padding: 4px 11px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    .key-status-pill.connected {
      background: var(--now-bg-surface-1, #dcfce7);
      color: var(--now-color-brand-green, #166534);
    }

    .key-status-pill.simulated {
      background: var(--now-bg-surface-1, #fef3c7);
      color: #92400e;
    }

    .masked-key-badge {
      display: inline-flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      background: var(--now-bg-surface-1, #f0fdf4);
      border: 1px solid var(--now-border-subtle, #bbf7d0);
      color: var(--now-color-brand-green, #14532d);
      padding: 7px 12px;
      border-radius: 8px;
      font-size: 12.5px;
      font-family: "JetBrains Mono", monospace;
    }

    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    @media (max-width: 780px) {
      .grid-2 {
        grid-template-columns: 1fr;
      }
    }

    .field {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .field label {
      font-size: 12.5px;
      font-weight: 600;
      color: var(--now-text-primary, #2c2e33);
    }

    .field-hint {
      font-size: 11.5px;
      color: var(--now-text-secondary, #6b7280);
    }

    .input-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    input[type="text"],
    input[type="password"],
    input[type="number"],
    input[type="email"],
    select {
      flex: 1;
      font-family: inherit;
      font-size: 13.5px;
      color: var(--now-text-primary, #16181d);
      background: var(--now-bg-surface-1, #fafaf9);
      border: 1px solid var(--now-border-subtle, #dcded9);
      border-radius: 10px;
      padding: 9px 12px;
      outline: none;
    }

    input:focus,
    select:focus {
      background: var(--now-bg-surface-0, #ffffff);
      border-color: var(--now-color-brand-green, #62d84e);
    }

    .toggle-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      background: var(--now-bg-surface-1, #fafaf9);
      border: 1px solid var(--now-border-subtle, #ececea);
      border-radius: 10px;
    }

    .toggle-label-group {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .toggle-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--now-text-primary, #16181d);
    }

    .toggle-sub {
      font-size: 11.5px;
      color: var(--now-text-secondary, #6b7280);
    }

    .actions-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-top: 6px;
    }

    .btn {
      position: relative;
      appearance: none;
      border: 1px solid var(--now-border-medium, #dcded9);
      background: var(--now-bg-surface-0, #ffffff);
      color: var(--now-text-primary, #16181d);
      font-size: 13px;
      font-weight: 600;
      padding: 8px 16px;
      border-radius: 999px;
      cursor: pointer;
      font-family: inherit;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: background 0.12s ease, border-color 0.12s ease;
    }

    .btn:hover {
      background: var(--now-bg-surface-1, #f4f4f2);
    }

    .btn.icon-btn {
      width: 36px;
      height: 36px;
      padding: 0;
      border-radius: 50%;
    }

    .btn.icon-btn svg {
      width: 17px;
      height: 17px;
      fill: currentColor;
    }

    .btn.primary {
      background: var(--now-color-brand-green, #62d84e);
      color: #032d42;
      border-color: var(--now-color-brand-green, #62d84e);
    }

    .btn.primary:hover {
      opacity: 0.9;
    }

    .btn.btn-delete-key {
      background: #fef2f2;
      color: #dc2626;
      border-color: #fecaca;
    }

    .btn.btn-delete-key:hover {
      background: #fee2e2;
    }

    .btn.btn-verify-key {
      background: var(--now-bg-surface-1, #f0fdf4);
      color: var(--now-color-brand-green, #166534);
      border-color: var(--now-border-subtle, #bbf7d0);
    }

    .btn.btn-verify-key:hover {
      opacity: 0.9;
    }

    .save-toast {
      font-size: 12.5px;
      font-weight: 600;
      color: #166534;
      background: #dcfce7;
      padding: 7px 14px;
      border-radius: 999px;
    }

    .masked-key-badge.locked {
      background: var(--now-bg-surface-1, #f8fafc);
      border: 1px solid var(--now-border-subtle, #cbd5e1);
      color: var(--now-text-primary, #334155);
      padding: 10px 14px;
      border-radius: 10px;
    }

    .key-info {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .key-badge-label {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--now-color-brand-green, #15803d);
    }

    .key-code {
      font-family: "JetBrains Mono", monospace;
      font-size: 13px;
      color: var(--now-text-primary, #0f172a);
      font-weight: 600;
    }

    .btn-delete-key {
      background: #fef2f2;
      border-color: #fecaca;
      color: #b91c1c;
      font-size: 12px;
      padding: 6px 12px;
    }

    .btn-delete-key:hover {
      background: #fee2e2;
      border-color: #fca5a5;
    }

    .btn-verify-key {
      background: #032d42;
      color: #ffffff;
      border-color: #032d42;
      white-space: nowrap;
    }

    .btn-verify-key:hover {
      background: #053b56;
    }

    .btn-verify-key:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .alert-hint {
      color: #b45309;
      font-weight: 500;
    }

    .error-banner {
      font-size: 12px;
      color: #dc2626;
      background: #fef2f2;
      border: 1px solid #fecaca;
      padding: 6px 10px;
      border-radius: 8px;
    }
  `;
