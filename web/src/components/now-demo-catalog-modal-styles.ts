// web/src/components/now-demo-catalog-modal-styles.ts
// Modal rules of the Artifact library (ADR-024): the media proofs viewer of <now-demo-catalog>
// and the deploy and clone dialogs, which reuse demoCatalogStyles. .modal-close is the 32px
// close button of all three.
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const demoCatalogModalStyles = css`
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

    /* Media proofs viewer. */
    .proofs-modal {
      width: 800px;
      max-width: 95vw;
      max-height: 85vh;
      overflow-y: auto;
    }

    .proofs-modal .modal-header h2 {
      font-size: 16px;
    }

    .proofs-sub {
      font-size: 12px;
      color: var(--now-text-secondary, #475467);
      margin-top: 4px;
    }

    .proofs-tools,
    .proof-links {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    /* #b42318 keeps 6:1 on the #f1f5f9 hover (#dc2626 was 4.4:1). */
    .btn-secondary.proof-danger {
      color: #b42318;
      border-color: #fca5a5;
      padding: 4px 10px;
    }

    .btn-secondary.proof-delete {
      font-size: 11px;
      padding: 2px 8px;
    }

    .icon-btn.modal-close {
      flex: 0 0 32px;
      width: 32px;
      height: 32px;
    }

    .modal-body.proofs-body {
      gap: 14px;
      padding: 10px 0;
    }

    .proofs-empty {
      font-size: 13px;
      color: var(--now-text-muted, #64748b);
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

    .proof-head,
    .proof-foot {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }

    .proof-label {
      font-weight: 600;
      font-size: 13px;
    }

    /* #047857 on #ecfdf5 is 5.2:1 (the old #16a34a was 3.1:1). */
    .proof-type {
      font-size: 11px;
      font-weight: 700;
      color: #047857;
      background: #ecfdf5;
      border: 1px solid #bbf7d0;
      padding: 1px 6px;
      border-radius: 999px;
    }

    .proof-foot {
      font-size: 11px;
      color: var(--now-text-secondary, #475467);
    }

    .proof-date {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .proof-link {
      display: inline-flex;
      align-items: center;
      color: #2563eb;
      font-weight: 600;
      text-decoration: none;
    }

    .proof-link.download {
      color: #047857;
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

    /* Phones (ADR-030): 40px touch targets in the proofs viewer and the dialogs. */
    @media (max-width: 768px), (max-height: 500px) {
      .modal-card .icon-btn {
        width: 40px;
        height: 40px;
        flex-basis: 40px;
      }

      .proof-link {
        min-height: 40px;
      }

      .proofs-modal .btn-secondary {
        min-width: 40px;
        min-height: 40px;
      }
    }
`;
