// web/src/views/now-synthesizer-view-styles.ts
// Styles of <now-synthesizer-view> in the Otto look (ADR-019; ADR-024: CSS beside its component).
// Author: Pierre Grothe
// Date: 2026-11-07
import { css } from 'lit';

export const synthesizerViewStyles = css`
      .synth-grid {
        display: grid;
        grid-template-columns: 420px minmax(0, 1fr);
        gap: 24px;
        align-items: start;
      }

      /* Narrow screens (ADR-030): the form above its result. */
      @media (max-width: 900px) {
        .synth-grid {
          grid-template-columns: minmax(0, 1fr);
          gap: 16px;
        }
      }

      .form-group {
        margin-bottom: 18px;
      }

      .form-label {
        display: block;
        font-size: 12.5px;
        font-weight: 600;
        color: var(--now-text-primary, #0f172a);
        margin-bottom: 6px;
      }

      .text-input, .select-input, .textarea-input {
        width: 100%;
        box-sizing: border-box;
        padding: 9px 12px;
        border-radius: var(--now-radius-md, 10px);
        border: 1px solid var(--now-border-subtle, #e2e8f0);
        background: var(--now-bg-surface-0, #ffffff);
        color: var(--now-text-primary, #0f172a);
        font-size: 13.5px;
        font-family: inherit;
        outline: none;
      }

      /* The objective reads like Otto's prompt: 16px/24px text in a softly rounded box. */
      .textarea-input {
        min-height: 132px;
        resize: vertical;
        padding: 14px 16px;
        border-radius: var(--now-radius-lg, 16px);
        font-size: 16px;
        line-height: 24px;
        background: #ffffff;
        box-shadow: 0 0 0 4px #f4f3f0;
      }

      .text-input:focus, .select-input:focus, .textarea-input:focus {
        border-color: var(--now-color-brand-green, #23a17e);
      }

      .action-row {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-top: 22px;
      }

      .primary-action-btn {
        min-height: 36px;
        padding: 8px 18px;
        background: var(--now-color-brand-green, #23a17e);
        color: #032d42;
        font: inherit;
        font-weight: 600;
        font-size: 13px;
        border: 1px solid var(--now-color-brand-green, #23a17e);
        border-radius: var(--now-radius-pill, 9999px);
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        white-space: nowrap;
        transition: background 0.15s ease;
      }

      .primary-action-btn:hover:not(:disabled) {
        background: var(--now-color-brand-green-hover, #1b8567);
      }

      .primary-action-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .form-alert {
        display: block;
        margin-top: 12px;
      }

      .result-head {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
      }

      .result-title {
        margin: 0 0 6px 0;
        font-size: 16px;
        font-weight: 700;
        color: var(--now-text-primary, #0f172a);
        overflow-wrap: anywhere;
      }

      .seed-status {
        display: block;
        margin-bottom: 12px;
      }

      /* Result tabs: Otto's warm segmented chips, the chosen one dark (as the settings menu). */
      .tabs-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        padding: 4px;
        border-radius: 12px;
        background: #f4f3f0;
        margin-bottom: 16px;
      }

      .tab-item {
        padding: 7px 14px;
        font: inherit;
        font-size: 13px;
        font-weight: 500;
        color: var(--now-text-primary, #0f172a);
        background: transparent;
        border: none;
        border-radius: var(--now-radius-md, 10px);
        cursor: pointer;
      }

      .tab-item:hover {
        background: var(--otto-canvas-active, #e3dfd8);
      }

      .tab-item.active {
        background: #1a1a1a;
        color: #ffffff;
      }

      .narrative {
        font-size: 14px;
        line-height: 1.6;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        color: var(--now-text-primary, #0f172a);
      }

      .code-preview {
        background: var(--now-text-primary, #0f172a);
        color: #f8fafc;
        border-radius: var(--now-radius-md, 10px);
        padding: 16px;
        font-family: var(--now-font-mono, monospace);
        font-size: 12px;
        line-height: 1.5;
        overflow-x: auto;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        margin: 0;
      }

      .empty-state {
        text-align: center;
        padding: 56px 20px;
        color: var(--now-text-secondary, #475467);
      }

      .empty-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--now-text-primary, #0f172a);
        margin-bottom: 6px;
      }

      .empty-hint {
        font-size: 13px;
      }

      /* Phones (ADR-030): 40px touch targets, a full-width action. */
      @media (max-width: 768px), (max-height: 500px) {
        .primary-action-btn {
          min-height: 40px;
        }

        .action-row .primary-action-btn {
          width: 100%;
        }

        .tab-item {
          min-height: 40px;
        }

        .textarea-input {
          min-height: 110px;
        }

        .empty-state {
          padding: 32px 12px;
        }
      }
`;
