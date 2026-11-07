// web/src/components/now-diagnostics-card-styles.ts
// Styles of <now-diagnostics-card>: the runtime telemetry strip.
// Author: Pierre Grothe
// Date: 2026-11-07

import { css } from 'lit';

export const diagnosticsCardStyles = css`
    :host {
      display: block;
    }

    /* Diagnostics Telemetry Strip */
    .diag-strip {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
    }

    @media (max-width: 768px) {
      .diag-strip {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    .diag-pill {
      background: var(--now-bg-surface-1, #f8fafc);
      border: 1px solid var(--now-border-subtle, #e2e8f0);
      border-radius: 10px;
      padding: 10px 14px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .diag-title {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--now-text-secondary, #64748b);
    }

    .diag-content {
      font-size: 13px;
      font-weight: 600;
      color: var(--now-text-primary, #0f172a);
      display: flex;
      align-items: center;
      gap: 6px;
    }
  `;
