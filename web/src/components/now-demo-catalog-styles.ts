// web/src/components/now-demo-catalog-styles.ts
// Styles of <now-demo-catalog> in the Otto look (ADR-019; ADR-024: CSS beside its component).
// The shared form rules (form-styles.ts) come first: the .btn-primary pill is the import
// button here and the primary action of the deploy and clone dialogs that reuse this sheet.
// The modal rules (those dialogs and the media proofs viewer) are in now-demo-catalog-modal-styles.ts.
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';
import { formStyles } from '../styles/form-styles.js';
import { demoCatalogModalStyles } from './now-demo-catalog-modal-styles.js';

export const demoCatalogStyles = [formStyles, css`
    :host {
      display: block;
      padding: 24px 36px;
      overflow-y: auto;
      height: 100%;
      background-color: var(--otto-canvas, #efece7);
    }

    .header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 24px;
    }

    .title-block h1 {
      margin: 0;
      font-size: 24px;
      font-weight: 500;
      color: var(--now-text-primary, #0f172a);
    }

    .title-block p {
      font-size: 13px;
      color: var(--now-text-secondary, #475467);
      margin: 4px 0 0;
    }

    .catalog-notice {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
      padding: 10px 16px;
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid rgba(0, 0, 0, 0.05);
      border-radius: var(--now-radius-md, 10px);
      font-size: 13px;
      overflow-wrap: anywhere;
    }

    .notice-close {
      flex-shrink: 0;
      min-width: 32px;
      min-height: 32px;
      background: none;
      border: none;
      border-radius: var(--now-radius-pill, 9999px);
      cursor: pointer;
      font-weight: 700;
      font-size: 14px;
      color: var(--now-text-secondary, #475467);
    }

    .notice-close:hover {
      background: #f4f3f0;
    }

    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(min(100%, 360px), 1fr));
      gap: 16px;
    }

    .demo-card {
      min-width: 0;
      background-color: var(--now-bg-surface-0, #ffffff);
      border: 1px solid rgba(0, 0, 0, 0.05);
      border-radius: var(--now-radius-lg, 16px);
      padding: 24px;
      display: flex;
      flex-direction: column;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
      transition: transform 0.15s ease, box-shadow 0.15s ease;
      position: relative;
    }

    .demo-card:hover {
      box-shadow: var(--now-shadow-soft, 0 4px 18px rgba(0, 0, 0, 0.05));
      transform: translateY(-2px);
    }

    .card-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 10px;
      margin-bottom: 10px;
    }

    .demo-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
      overflow-wrap: anywhere;
    }

    .release-badge {
      flex-shrink: 0;
      font-size: 11.5px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: var(--now-radius-pill, 9999px);
      background-color: #ecfdf5;
      color: #047857;
    }

    .demo-desc {
      font-size: 13px;
      color: var(--now-text-secondary, #475467);
      flex: 1;
      margin: 0 0 16px;
      line-height: 1.5;
    }

    .metadata-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 16px;
      padding: 10px 0;
      border-top: 1px solid #f4f3f0;
      border-bottom: 1px solid #f4f3f0;
      margin-bottom: 16px;
      font-size: 12px;
      color: var(--now-text-muted, #64748b);
    }

    .meta-item {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .meta-val {
      color: var(--now-text-primary, #0f172a);
      font-weight: 600;
    }

    .tags-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 16px;
    }

    .tag-pill {
      font-size: 11.5px;
      font-weight: 500;
      background-color: #f4f3f0;
      color: var(--now-text-secondary, #475467);
      padding: 2px 10px;
      border-radius: var(--now-radius-pill, 9999px);
    }

    .card-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .btn-secondary {
      background-color: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-medium);
      color: var(--now-text-primary);
      padding: 6px 12px;
      border-radius: var(--now-radius-sm);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: background-color 0.15s ease;
      flex: 1;
      justify-content: center;
    }

    .btn-secondary:hover {
      background-color: var(--now-bg-surface-1);
    }

    .btn-danger {
      color: #dc2626 !important;
      border-color: #fecaca !important;
    }

    .btn-danger:hover {
      background-color: #fef2f2 !important;
      border-color: #dc2626 !important;
    }

    .btn-otto {
      background-color: #faf5ff;
      border: 1px solid #e9d5ff;
      color: #7e22ce;
      padding: 6px 12px;
      border-radius: var(--now-radius-sm);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 4px;
      transition: background-color 0.15s ease;
    }

    .btn-otto:hover {
      background-color: #f3e8ff;
    }

    .ownership-row {
      margin: -2px 0 6px;
    }

    .own-chip {
      display: inline-block;
      font-size: 11.5px;
      padding: 2px 8px;
      border-radius: 999px;
      background: #efece7;
      color: #3f4148;
      overflow-wrap: anywhere;
    }

    .own-chip.shared {
      background: #e3eefc;
      color: #1f3a5f;
    }

    .icon-btn {
      position: relative;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0;
      width: 36px;
      height: 36px;
      border-radius: var(--now-radius-sm, 6px);
      flex: 0 0 36px;
    }

    .icon-btn svg {
      width: 17px;
      height: 17px;
      fill: currentColor;
    }

    /* The library's own icon buttons are round, as the Otto toolbar buttons. */
    .header-row .icon-btn,
    .card-actions .icon-btn {
      border-radius: var(--now-radius-pill, 9999px);
    }

    .card-actions .btn-secondary:not(.btn-danger) {
      border-color: var(--now-border-subtle, #e2e8f0);
    }

    .card-actions .btn-secondary:hover {
      background-color: #f4f3f0;
    }

    .card-date-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 11.5px;
      color: var(--now-text-secondary, #475467);
      margin-bottom: 8px;
    }

    .media-proofs-bar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 8px 12px;
      background: #f4f3f0;
      border-radius: var(--now-radius-md, 10px);
      margin-bottom: 14px;
      font-size: 12px;
    }

    .media-proofs-summary {
      display: flex;
      align-items: center;
      gap: 6px;
      min-width: 0;
      color: var(--now-text-secondary, #475467);
    }

    .btn-proofs {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      color: #1d4ed8;
      font: inherit;
      font-size: 11.5px;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: var(--now-radius-pill, 9999px);
      cursor: pointer;
    }

    .btn-proofs:hover {
      background: #dbeafe;
    }

    /* Phones (ADR-030): 12px gutters and 40px touch targets. */
    @media (max-width: 768px), (max-height: 500px) {
      :host {
        padding: 16px 12px;
      }

      .title-block h1 {
        font-size: 20px;
      }

      .demo-card {
        padding: 16px;
      }

      .header-row .icon-btn,
      .card-actions .icon-btn {
        width: 40px;
        height: 40px;
        flex-basis: 40px;
      }

      .notice-close,
      .btn-proofs {
        min-width: 40px;
        min-height: 40px;
      }
    }
`, demoCatalogModalStyles];
