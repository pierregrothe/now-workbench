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

      .action-row {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-top: 22px;
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

      /* Result tabs: the shared segmented chips (form-styles.ts), wrapping on narrow screens. */
      .tabs-bar {
        flex-wrap: wrap;
        margin-bottom: 16px;
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

      /* Phones (ADR-030): a full-width action (touch targets are in form-styles.ts). */
      @media (max-width: 768px), (max-height: 500px) {
        .action-row .btn-primary {
          width: 100%;
        }

        .textarea-input {
          min-height: 110px;
        }

        .empty-state {
          padding: 32px 12px;
        }
      }
`;
