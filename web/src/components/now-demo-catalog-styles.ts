// web/src/components/now-demo-catalog-styles.ts
// Styles of <now-demo-catalog> (ADR-024: CSS lives beside its component).
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const demoCatalogStyles = css`
    :host {
      display: block;
      padding: 24px 32px;
      overflow-y: auto;
      height: 100%;
      background-color: var(--now-bg-canvas);
    }

    .header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }

    .title-block h1 {
      font-size: 20px;
      font-weight: 700;
      color: var(--now-text-primary);
    }

    .title-block p {
      font-size: 13px;
      color: var(--now-text-secondary);
      margin-top: 4px;
    }

    .btn-primary {
      background-color: var(--now-color-brand-green);
      color: #ffffff;
      font-weight: 600;
      font-size: 13px;
      padding: 8px 16px;
      border-radius: var(--now-radius-sm);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: background-color 0.15s ease;
    }

    .btn-primary:hover {
      background-color: var(--now-color-brand-green-hover);
    }

    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 20px;
    }

    .demo-card {
      background-color: var(--now-bg-surface-0, #ffffff);
      border: 1px solid rgba(0, 0, 0, 0.05);
      border-radius: 16px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      box-shadow: 0 1px 2px 0 rgba(15, 23, 42, 0.03);
      transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
      position: relative;
    }

    .demo-card:hover {
      border-color: rgba(0, 0, 0, 0.12);
      box-shadow: 0 8px 16px -2px rgba(15, 23, 42, 0.08);
      transform: translateY(-2px);
    }

    .card-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 10px;
    }

    .demo-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--now-text-primary);
    }

    .release-badge {
      font-size: 11px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: var(--now-radius-pill);
      background-color: #f0fdf4;
      color: #16a34a;
      border: 1px solid #bbf7d0;
    }

    .demo-desc {
      font-size: 13px;
      color: var(--now-text-secondary);
      flex: 1;
      margin-bottom: 16px;
      line-height: 1.5;
    }

    .metadata-bar {
      display: flex;
      gap: 16px;
      padding: 10px 0;
      border-top: 1px solid var(--now-border-subtle);
      border-bottom: 1px solid var(--now-border-subtle);
      margin-bottom: 16px;
      font-size: 12px;
      color: var(--now-text-muted);
    }

    .meta-item {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .meta-val {
      color: var(--now-text-primary);
      font-weight: 600;
    }

    .tags-row {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 16px;
    }

    .tag-pill {
      font-size: 11px;
      font-weight: 500;
      background-color: var(--now-bg-surface-1);
      color: var(--now-text-secondary);
      padding: 2px 8px;
      border-radius: var(--now-radius-pill);
      border: 1px solid var(--now-border-subtle);
    }

    .card-actions {
      display: flex;
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

    .modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.5);
      backdrop-filter: blur(4px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .modal-card {
      background: var(--now-bg-surface-0, #ffffff);
      border-radius: var(--now-radius-md, 8px);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
      width: 480px;
      max-width: 90vw;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .modal-header h2 {
      font-size: 17px;
      font-weight: 700;
      color: var(--now-text-primary, #0f172a);
      margin: 0;
    }

    .modal-body {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .modal-input-field {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .modal-input-field label {
      font-size: 12px;
      font-weight: 600;
      color: var(--now-text-primary, #334155);
    }

    .modal-input-field input {
      font-size: 13px;
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid var(--now-border-medium, #cbd5e1);
      background: var(--now-bg-surface-1, #fafaf9);
      color: var(--now-text-primary, #111827);
      outline: none;
    }

    .modal-input-field input:focus {
      border-color: var(--now-color-brand-green, #23a17e);
    }

    .modal-error {
      font-size: 12px;
      color: #dc2626;
      background: #fef2f2;
      border: 1px solid #fecaca;
      padding: 6px 10px;
      border-radius: 6px;
    }

    .modal-footer {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 8px;
    }

    .card-date-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 11px;
      color: var(--now-text-secondary, #64748b);
      margin-bottom: 8px;
    }

    .media-proofs-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 10px;
      background: var(--now-bg-surface-1, #f8fafc);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: var(--now-radius-sm, 6px);
      margin-bottom: 14px;
      font-size: 11.5px;
    }

    .media-proofs-summary {
      display: flex;
      align-items: center;
      gap: 6px;
      color: var(--now-text-secondary, #475569);
    }

    .btn-proofs {
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      color: #1d4ed8;
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 4px;
      cursor: pointer;
    }

    .btn-proofs:hover {
      background: #dbeafe;
    }

    .proof-item {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 12px;
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: 8px;
      background: var(--now-bg-surface-1, #f8fafc);
    }

    .proof-media-wrapper {
      max-height: 220px;
      border-radius: 6px;
      overflow: hidden;
      background: #032d42;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .proof-media-wrapper img,
    .proof-media-wrapper video {
      max-width: 100%;
      max-height: 220px;
      object-fit: contain;
    }
  `;
