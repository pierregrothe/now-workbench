// web/src/components/admin-shared-styles.ts
// Section cards, badges, buttons and feedback shared by the instance admin elements (ADR-024).
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const adminSharedStyles = css`
    /* Section Cards */
    .section-card {
      background: var(--now-bg-surface-0, #ffffff);
      border: 1px solid var(--now-border-subtle, #e4e5e1);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
      display: flex;
      flex-direction: column;
      gap: 18px;
    }

    .section-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .section-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--now-text-primary, #0b0f19);
      margin: 0;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .section-desc {
      font-size: 13px;
      color: var(--now-text-secondary, #6b7280);
      margin: 4px 0 0 0;
    }

    /* Badges */
    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 11.5px;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 999px;
      white-space: nowrap;
    }

    .status-badge.authenticated {
      background: #f0fdf4;
      color: #15803d;
      border: 1px solid #bbf7d0;
    }

    .status-badge.auth_failed, .status-badge.error {
      background: #fef2f2;
      color: #b91c1c;
      border: 1px solid #fecaca;
    }

    .status-badge.testing {
      background: #eff6ff;
      color: #1d4ed8;
      border: 1px solid #bfdbfe;
    }

    .status-badge.unknown {
      background: var(--now-bg-surface-1, #f3f4f6);
      color: var(--now-text-secondary, #4b5563);
      border: 1px solid var(--now-border-subtle, #e5e7eb);
    }

    .dot-indicator {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: currentColor;
    }

    /* Buttons */
    .btn-action {
      position: relative;
      appearance: none;
      border: 1px solid var(--now-border-subtle, #d1d5db);
      background: var(--now-bg-surface-0, #ffffff);
      color: var(--now-text-primary, #374151);
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-family: inherit;
      transition: all 0.12s ease;
    }

    .btn-action.icon-btn {
      width: 30px;
      height: 30px;
      padding: 0;
      justify-content: center;
      border-radius: 6px;
    }

    .btn-action.icon-btn svg {
      width: 15px;
      height: 15px;
      fill: currentColor;
    }

    .btn-action:hover {
      background: var(--now-bg-surface-1, #f3f4f6);
      border-color: var(--now-border-medium, #9ca3af);
      color: var(--now-text-primary, #111827);
    }

    .btn-action.primary {
      background: var(--now-color-brand-green, #62d84e);
      color: #032d42;
      border-color: var(--now-color-brand-green, #62d84e);
    }

    .btn-action.primary:hover {
      opacity: 0.9;
    }

    .badge-active-pill {
      font-size: 11.5px;
      font-weight: 700;
      color: #15803d;
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      padding: 3px 8px;
      border-radius: 999px;
    }

    .badge-active-pill.icon-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 30px;
      height: 30px;
      padding: 0;
      border-radius: 6px;
      position: relative;
    }

    .badge-active-pill.icon-btn svg {
      width: 16px;
      height: 16px;
      fill: #15803d;
    }

    .btn-danger {
      position: relative;
      appearance: none;
      background: #fef2f2;
      border: 1px solid #fecaca;
      color: #b91c1c;
      padding: 5px 10px;
      border-radius: 6px;
      font-size: 11.5px;
      font-weight: 600;
      cursor: pointer;
      font-family: inherit;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: all 0.12s ease;
    }

    .btn-danger.icon-btn {
      width: 30px;
      height: 30px;
      padding: 0;
      justify-content: center;
      border-radius: 6px;
    }

    .btn-danger.icon-btn svg {
      width: 15px;
      height: 15px;
      fill: currentColor;
    }

    .btn-danger:hover {
      background: #fee2e2;
      border-color: #fca5a5;
    }

    .btn-danger:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .inline-edit-panel {
      background: var(--now-bg-surface-1, #f8fafc);
      border: 1px solid var(--now-border-subtle, #cbd5e1);
      border-radius: 10px;
      padding: 16px 20px;
      margin: 8px 0;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .edit-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
    }

    @media (max-width: 768px) {
      .edit-grid {
        grid-template-columns: 1fr;
      }

      /* Phones (ADR-030): headers wrap their badge under the title. */
      .section-card {
        padding: 16px;
      }

      .section-header {
        flex-wrap: wrap;
        gap: 8px;
      }
    }

    .edit-actions {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-top: 8px;
      border-top: 1px solid var(--now-border-subtle, #e2e8f0);
    }


    /* Action feedback */
    .status-feedback {
      font-size: 12.5px;
      padding: 8px 14px;
      border-radius: 8px;
      font-weight: 500;
    }

    .status-feedback.success {
      background: #f0fdf4;
      color: #15803d;
      border: 1px solid #bbf7d0;
    }

    .status-feedback.error {
      background: #fef2f2;
      color: #b91c1c;
      border: 1px solid #fecaca;
    }

    /* Form fields (add form and the table's inline edit row) */
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .form-label {
      font-size: 12.5px;
      font-weight: 600;
      color: var(--now-text-secondary, #374151);
    }

    .form-input {
      font-family: inherit;
      font-size: 13.5px;
      padding: 9px 12px;
      border: 1px solid var(--now-border-subtle, #d1d5db);
      border-radius: 8px;
      background: var(--now-bg-surface-1, #fafaf9);
      color: var(--now-text-primary, #111827);
      outline: none;
    }

    .form-input:focus {
      background: var(--now-bg-surface-0, #ffffff);
      border-color: var(--now-color-brand-green, #032d42);
    }
  `;
