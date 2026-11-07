// web/src/components/now-presenter-hud-styles.ts
// Styles of <now-presenter-hud> (ADR-024: CSS lives beside its component).
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const presenterHudStyles = css`
    :host {
      display: block;
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 1000;
      font-family: var(--now-font-family, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif);
      color: var(--now-text-primary, #ffffff);
    }

    .hud-card {
      background: var(--now-bg-surface, #1e242b);
      border: 1px solid var(--now-border-color, #2e3742);
      border-radius: 8px;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
      width: 440px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: all 0.2s ease-in-out;
    }

    .safe-harbor-bar {
      background: #0f1318;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      padding: 6px 14px;
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 11px;
      color: #94a3b8;
    }

    .safe-harbor-tag {
      background: rgba(234, 179, 8, 0.15);
      border: 1px solid rgba(234, 179, 8, 0.4);
      color: #facc15;
      font-size: 9.5px;
      font-weight: 700;
      text-transform: uppercase;
      padding: 1px 5px;
      border-radius: 3px;
      letter-spacing: 0.5px;
      white-space: nowrap;
    }

    .safe-harbor-text {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .hud-header {
      background: #181d24;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--now-border-color, #2e3742);
    }

    .hud-title-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .badge-presenter {
      background: #23a17e;
      color: #ffffff;
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      padding: 2px 6px;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }

    .demo-title {
      font-size: 13px;
      font-weight: 600;
      color: #ffffff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 220px;
    }

    .close-btn {
      position: relative;
      background: transparent;
      border: none;
      color: var(--now-text-muted, #8b9baa);
      cursor: pointer;
      padding: 0;
      width: 26px;
      height: 26px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
    }

    .close-btn svg {
      width: 15px;
      height: 15px;
      fill: currentColor;
    }

    .close-btn:hover {
      color: #ffffff;
      background: rgba(255, 255, 255, 0.1);
    }

    .hud-body {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      max-height: 480px;
      overflow-y: auto;
    }

    .stage-indicator {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
      color: var(--now-text-muted, #8b9baa);
    }

    .stage-title {
      font-size: 15px;
      font-weight: 700;
      color: #ffffff;
      margin-top: 4px;
    }

    .persona-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(35, 161, 126, 0.12);
      border: 1px solid rgba(35, 161, 126, 0.35);
      color: #38c89b;
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 11.5px;
      font-weight: 600;
      margin-top: 4px;
    }

    .section-title {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--now-text-muted, #8b9baa);
      margin-bottom: 4px;
    }

    .talking-points-list {
      background: #15191f;
      border-left: 3px solid #23a17e;
      padding: 10px 12px;
      border-radius: 0 4px 4px 0;
      margin: 0;
      list-style-type: none;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .talking-points-list li {
      font-size: 12.5px;
      line-height: 1.45;
      color: #e2e8f0;
      display: flex;
      align-items: flex-start;
      gap: 6px;
    }

    .talking-points-list li::before {
      content: '';
      color: #23a17e;
      font-size: 10px;
      margin-top: 2px;
    }

    .instructions-list {
      margin: 0;
      padding-left: 18px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .instructions-list li {
      font-size: 12px;
      color: var(--now-text-secondary, #cbd5e1);
      line-height: 1.4;
    }

    .verification-status {
      font-size: 11.5px;
      padding: 8px 12px;
      border-radius: 4px;
      margin-top: 4px;
    }

    .verification-status.success {
      background: rgba(35, 161, 126, 0.15);
      color: #38c89b;
      border: 1px solid rgba(35, 161, 126, 0.3);
    }

    .verification-status.pending {
      background: rgba(234, 179, 8, 0.12);
      color: #facc15;
      border: 1px solid rgba(234, 179, 8, 0.25);
    }

    .hud-footer {
      background: #181d24;
      padding: 12px 16px;
      border-top: 1px solid var(--now-border-color, #2e3742);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .btn {
      position: relative;
      font-size: 12px;
      font-weight: 600;
      padding: 6px 14px;
      border-radius: 4px;
      cursor: pointer;
      border: none;
      transition: background 0.15s ease;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .btn.icon-btn {
      width: 32px;
      height: 32px;
      padding: 0;
      border-radius: 6px;
    }

    .btn.icon-btn svg {
      width: 16px;
      height: 16px;
      fill: currentColor;
    }

    .btn-secondary {
      background: #2e3742;
      color: #ffffff;
    }

    .btn-secondary:hover:not(:disabled) {
      background: #3c4755;
    }

    .btn-primary {
      background: #23a17e;
      color: #ffffff;
    }

    .btn-primary:hover:not(:disabled) {
      background: #1e876a;
    }

    .btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
  `;
