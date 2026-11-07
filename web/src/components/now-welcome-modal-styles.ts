// web/src/components/now-welcome-modal-styles.ts
// Styles of <now-welcome-modal> (ADR-024: CSS lives beside its component).
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const welcomeModalStyles = css`
    :host {
      display: block;
      font-family: "Plus Jakarta Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .backdrop {
      position: fixed;
      inset: 0;
      background: rgba(15, 20, 25, 0.35);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 2000;
      padding: 24px;
    }

    .modal {
      width: 920px;
      max-width: 96vw;
      height: 600px;
      max-height: 90vh;
      background: var(--now-bg-surface-0, #ffffff);
      border-radius: 16px;
      box-shadow: 0 24px 64px rgba(0, 0, 0, 0.22);
      display: grid;
      grid-template-columns: 320px 1fr;
      overflow: hidden;
      position: relative;
    }

    .modal-sidebar {
      background: var(--now-bg-surface-0, #ffffff);
      padding: 36px 24px 28px 28px;
      display: flex;
      flex-direction: column;
      border-right: 1px solid var(--now-border-subtle, #ececeb);
    }

    .new-pill {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      align-self: flex-start;
      background: #dbeafe;
      color: #1d4ed8;
      font-size: 12px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 999px;
      margin-bottom: 14px;
    }

    .new-pill svg {
      width: 13px;
      height: 13px;
      fill: currentColor;
    }

    .modal-heading {
      font-size: 24px;
      font-weight: 700;
      color: var(--now-text-primary, #0b0f19);
      line-height: 1.25;
      letter-spacing: -0.02em;
      margin: 0 0 28px 0;
    }

    .tab-list {
      display: flex;
      flex-direction: column;
      gap: 2px;
      flex: 1;
    }

    .tab-btn {
      appearance: none;
      border: none;
      border-left: 4px solid transparent;
      background: transparent;
      text-align: left;
      padding: 13px 16px;
      font-size: 14.5px;
      font-weight: 400;
      color: var(--now-text-secondary, #2c2e33);
      cursor: pointer;
      transition: background 0.12s ease, color 0.12s ease;
      font-family: inherit;
    }

    .tab-btn:hover {
      background: var(--now-bg-surface-1, #f6f6f5);
    }

    .tab-btn.active {
      border-left-color: var(--now-color-brand-green, #62d84e);
      background: var(--now-bg-surface-1, #f1f2f1);
      font-weight: 600;
      color: var(--now-text-primary, #0b0f19);
    }

    .sidebar-footer {
      padding-top: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .enter-btn {
      position: relative;
      appearance: none;
      border: 1px solid var(--now-color-brand-green, #62d84e);
      background: var(--now-color-brand-green, #62d84e);
      color: #032d42;
      font-size: 13px;
      font-weight: 600;
      padding: 9px 18px;
      border-radius: 999px;
      cursor: pointer;
      transition: background 0.12s ease;
      font-family: inherit;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .enter-btn.icon-btn {
      width: 36px;
      height: 36px;
      padding: 0;
      border-radius: 50%;
    }

    .enter-btn.icon-btn svg {
      width: 17px;
      height: 17px;
      fill: currentColor;
    }

    .enter-btn:hover {
      opacity: 0.9;
    }

    .modal-body {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: var(--now-bg-surface-0, #ffffff);
    }

    .visual-stage {
      flex: 1;
      background: var(--now-bg-canvas, #f2f2ef);
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 28px 36px 0 36px;
      overflow: hidden;
    }

    .close-icon-btn {
      position: absolute;
      top: 16px;
      right: 16px;
      width: 32px;
      height: 32px;
      border-radius: 999px;
      border: none;
      background: var(--now-bg-surface-0, rgba(255, 255, 255, 0.85));
      color: var(--now-text-secondary, #4b5563);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      z-index: 5;
      transition: background 0.12s ease, color 0.12s ease;
    }

    .close-icon-btn:hover {
      background: var(--now-bg-surface-1, #ffffff);
      color: var(--now-text-primary, #0b0f19);
    }

    .close-icon-btn svg {
      width: 16px;
      height: 16px;
      stroke: currentColor;
      stroke-width: 2;
      fill: none;
    }

    .preview-card {
      width: 100%;
      height: 100%;
      background: var(--now-bg-surface-0, #ffffff);
      border-radius: 14px 14px 0 0;
      box-shadow: 0 8px 30px var(--now-shadow-soft, rgba(0, 0, 0, 0.06));
      padding: 24px 28px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .preview-card-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--now-border-subtle, #f0f0ee);
      padding-bottom: 14px;
    }

    .preview-brand {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      font-weight: 700;
      color: var(--now-text-primary, #0b0f19);
    }

    .preview-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--now-color-brand-green, #62d84e);
    }

    .preview-badge {
      font-size: 11px;
      font-weight: 600;
      color: var(--now-text-primary, #032d42);
      background: var(--now-bg-surface-1, #e8f5e9);
      padding: 3px 9px;
      border-radius: 999px;
    }

    .preview-skeleton {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-top: 18px;
    }

    .skeleton-line {
      height: 10px;
      border-radius: 6px;
      background: var(--now-bg-surface-1, #f3f4f3);
    }

    .skeleton-line.w-70 {
      width: 70%;
    }

    .skeleton-line.w-90 {
      width: 90%;
    }

    .skeleton-line.w-55 {
      width: 55%;
    }

    .preview-cards-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-top: auto;
      padding-top: 16px;
    }

    .mini-tile {
      background: var(--now-bg-surface-1, #fafaf9);
      border: 1px solid var(--now-border-subtle, #ececea);
      border-radius: 8px;
      padding: 10px;
      font-size: 11px;
      font-weight: 600;
      color: var(--now-text-primary, #374151);
    }

    .mini-tile span {
      display: block;
      font-size: 10px;
      font-weight: 400;
      color: var(--now-text-secondary, #6b7280);
      margin-top: 3px;
    }

    .narrative-pane {
      border-top: 1px solid var(--now-border-subtle, #e5e5e3);
      padding: 24px 32px 24px 32px;
      background: var(--now-bg-surface-0, #ffffff);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .narrative-title {
      font-size: 20px;
      font-weight: 700;
      color: var(--now-text-primary, #0b0f19);
      margin: 0;
      letter-spacing: -0.015em;
    }

    .narrative-desc {
      font-size: 14px;
      line-height: 1.55;
      color: var(--now-text-secondary, #374151);
      margin: 0;
    }

    .save-error {
      font-size: 12.5px;
      color: #b42318;
    }

    .modal-nav-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid var(--now-border-subtle, #f0f0ee);
      gap: 12px;
    }

    .dont-show-checkbox {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 12.5px;
      color: var(--now-text-secondary, #475467);
      cursor: pointer;
      user-select: none;
    }

    .dont-show-checkbox input[type="checkbox"] {
      width: 16px;
      height: 16px;
      accent-color: var(--now-color-brand-green, #23a17e);
      cursor: pointer;
    }

    .nav-buttons-group {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .pill-btn {
      appearance: none;
      border: 1px solid var(--now-border-medium, #cbd5e1);
      background: var(--now-bg-surface-0, #ffffff);
      color: var(--now-text-primary, #0f172a);
      font-size: 13px;
      font-weight: 600;
      padding: 7px 18px;
      border-radius: 999px;
      cursor: pointer;
      font-family: inherit;
      transition: all 0.12s ease;
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .pill-btn:hover {
      background: var(--now-bg-surface-1, #f8fafc);
      border-color: var(--now-border-subtle, #94a3b8);
    }

    .pill-btn.primary {
      background: var(--now-color-brand-green, #23a17e);
      color: #ffffff;
      border-color: var(--now-color-brand-green, #23a17e);
    }

    .pill-btn.primary:hover {
      background: var(--now-color-brand-green-hover, #1b8567);
      border-color: var(--now-color-brand-green-hover, #1b8567);
    }

    .pill-btn.secondary {
      background: var(--now-bg-surface-1, #f1f5f9);
      border-color: var(--now-border-subtle, #e2e8f0);
      color: var(--now-text-secondary, #475467);
    }

    .step-counter {
      font-size: 12px;
      font-weight: 600;
      color: var(--now-text-muted, #64748b);
    }
  
    /* Phones (ADR-030): steps become a strip above the story; the preview art is dropped. */
    @media (max-width: 768px), (max-height: 500px) {
      .backdrop {
        padding: calc(8px + env(safe-area-inset-top, 0px)) 8px calc(8px + env(safe-area-inset-bottom, 0px));
      }

      .modal {
        width: 100%;
        max-width: none;
        height: 100%;
        max-height: none;
        grid-template-columns: minmax(0, 1fr);
        grid-template-rows: auto minmax(0, 1fr);
      }

      .modal-sidebar {
        padding: 16px 16px 8px;
        border-right: none;
        border-bottom: 1px solid var(--now-border-subtle, #ececeb);
      }

      .modal-heading {
        font-size: 19px;
        margin-bottom: 10px;
      }

      .tab-list {
        flex-direction: row;
        overflow-x: auto;
        scrollbar-width: none;
      }

      .tab-btn {
        flex-shrink: 0;
        white-space: nowrap;
        border-left: none;
        border-bottom: 3px solid transparent;
        padding: 10px 12px;
      }

      .tab-btn.active {
        border-bottom-color: var(--now-color-brand-green, #62d84e);
      }

      .visual-stage {
        display: none;
      }

      .modal-body {
        overflow-y: auto;
      }

      .narrative-pane {
        border-top: none;
        padding: 16px;
        flex: 1;
      }

      .modal-nav-row {
        flex-wrap: wrap;
      }
    }
`;
