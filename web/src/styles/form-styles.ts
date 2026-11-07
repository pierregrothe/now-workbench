// web/src/styles/form-styles.ts
// Shared Otto-look form rules (ADR-019; ADR-024 rule 1): labels, fields, segmented chips, pill button.
// Used by the Synthesizer and Media Capture views; each view keeps only its own differences.
// Author: Pierre Grothe
// Date: 2026-11-07
import { css } from 'lit';

export const formStyles = css`
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

      .text-input:focus, .select-input:focus, .textarea-input:focus {
        border-color: var(--now-color-brand-green, #23a17e);
      }

      /* Otto's warm segmented chips, the chosen one dark (as the settings menu). */
      .seg {
        display: flex;
        gap: 4px;
        padding: 4px;
        border-radius: 12px;
        background: #f4f3f0;
      }

      .seg-item {
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

      .seg-item:hover {
        background: var(--otto-canvas-active, #e3dfd8);
      }

      .seg-item.active {
        background: #1a1a1a;
        color: #ffffff;
      }

      /* The primary action: a brand-green pill, as the settings primary button. */
      .btn-primary {
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

      .btn-primary:hover:not(:disabled) {
        background: var(--now-color-brand-green-hover, #1b8567);
      }

      .btn-primary:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      /* Phones (ADR-030): 40px touch targets. */
      @media (max-width: 768px), (max-height: 500px) {
        .seg-item,
        .btn-primary {
          min-height: 40px;
        }
      }
`;
