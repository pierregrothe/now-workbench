// web/src/views/now-capture-studio-styles.ts
// Styles of <now-capture-studio> in the Otto look (ADR-019; ADR-024: CSS beside its component).
// Author: Pierre Grothe
// Date: 2026-11-07
import { css } from 'lit';

export const captureStudioStyles = css`
      .studio-grid {
        display: grid;
        grid-template-columns: 360px minmax(0, 1fr);
        gap: 24px;
        align-items: start;
      }

      /* Narrow screens (ADR-030): the form above its result. */
      @media (max-width: 900px) {
        .studio-grid {
          grid-template-columns: minmax(0, 1fr);
          gap: 16px;
        }
      }

      /* Capture mode: the shared segmented chips (form-styles.ts), two equal halves. */
      .mode-btn {
        flex: 1;
        min-width: 0;
        padding: 7px 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
      }

      .capture-action {
        margin-top: 22px;
      }

      .capture-btn {
        width: 100%;
      }

      .capture-status {
        display: block;
        margin-top: 14px;
      }

      .gallery-head {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
      }

      .gallery-title {
        margin: 0;
        font-size: 16px;
        font-weight: 700;
        color: var(--now-text-primary, #0f172a);
      }

      .gallery-tools {
        display: flex;
        gap: 8px;
      }

      .gallery-empty {
        text-align: center;
        padding: 48px 20px;
        color: var(--now-text-secondary, #475467);
        overflow-wrap: anywhere;
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

      .gallery-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(min(100%, 260px), 1fr));
        gap: 16px;
      }

      .artifact-card {
        background: var(--now-bg-surface-0, #ffffff);
        border: 1px solid rgba(0, 0, 0, 0.05);
        border-radius: var(--now-radius-lg, 16px);
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
        overflow: hidden;
        display: flex;
        flex-direction: column;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
      }

      .artifact-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--now-shadow-soft, 0 4px 18px rgba(0, 0, 0, 0.05));
      }

      .thumbnail-container {
        height: 160px;
        background: var(--otto-canvas-active, #e3dfd8);
        position: relative;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .thumbnail-container img, .thumbnail-container video {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }

      .play-overlay {
        position: absolute;
        width: 40px;
        height: 40px;
        background: rgba(0, 0, 0, 0.65);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #ffffff;
        pointer-events: none;
      }

      .play-overlay svg {
        width: 20px;
        height: 20px;
        fill: currentColor;
      }

      .artifact-info {
        padding: 14px 16px 12px;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }

      .artifact-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--now-text-primary, #0f172a);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .artifact-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 12px;
        color: var(--now-text-secondary, #475467);
      }

      .card-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        padding: 10px 16px 14px;
      }

      .small-btn {
        padding: 5px 12px;
        font: inherit;
        font-size: 12px;
        font-weight: 600;
        border-radius: var(--now-radius-pill, 9999px);
        border: 1px solid var(--now-border-medium, #cbd5e1);
        background: var(--now-bg-surface-0, #ffffff);
        color: var(--now-text-primary, #0f172a);
        cursor: pointer;
      }

      .small-btn:hover {
        background: #f4f3f0;
      }

      .small-btn.danger {
        color: var(--now-status-error, #dc2626);
        border-color: #fecaca;
      }

      .small-btn.danger:hover {
        background: #fef2f2;
      }

      /* Phones (ADR-030): 40px touch targets. */
      @media (max-width: 768px), (max-height: 500px) {
        .small-btn {
          min-height: 40px;
        }

        .gallery-empty {
          padding: 32px 12px;
        }
      }
`;
