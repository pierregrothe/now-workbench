// web/src/components/now-instance-add-form-styles.ts
// Styles of <now-instance-add-form>: the connect-an-instance form.
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const instanceAddFormStyles = css`
    :host {
      display: block;
    }

    /* Add Instance Form */
    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }

    @media (max-width: 768px) {
      .form-grid {
        grid-template-columns: 1fr;
      }
    }





    .form-toggle-row {
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 13px;
      font-weight: 500;
      color: var(--now-text-primary, #374151);
      padding: 4px 0;
    }

    .form-actions-row {
      grid-column: 1 / -1;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 12px;
      padding-top: 8px;
    }

    .btn-register {
      appearance: none;
      border: none;
      background: var(--now-color-brand-green, #62d84e);
      color: #032d42;
      padding: 9px 20px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-family: inherit;
      transition: background 0.15s ease;
    }

    .btn-register:hover {
      opacity: 0.9;
    }

    .btn-register.icon-btn {
      width: 36px;
      height: 36px;
      padding: 0;
      justify-content: center;
      border-radius: 50%;
    }

    .btn-register.icon-btn svg {
      width: 18px;
      height: 18px;
      fill: currentColor;
    }

    .btn-register:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  `;
