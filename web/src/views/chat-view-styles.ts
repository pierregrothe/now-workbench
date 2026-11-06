// web/src/views/chat-view-styles.ts
// Styles for the Otto chat view (home hero, conversation column, docked prompt, approval cards).
// Author: Pierre Grothe
// Date: 2026-11-06
import { css } from 'lit';

export const chatViewStyles = css`
      .split {
        flex: 1;
        min-height: 0;
        display: flex;
      }

      .split .scroll-canvas {
        flex: 1;
        min-width: 0;
      }

      .dash-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
      }

      .dash-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 13px;
        font-weight: 600;
        color: var(--now-text-secondary, #4b5563);
      }

      .dash-metric {
        font-size: 22px;
        font-weight: 600;
        margin: 8px 0 2px;
      }

      .dash-sub {
        font-size: 12.5px;
        color: var(--now-text-secondary, #4b5563);
        margin: 0 0 8px;
      }

      .open-btn {
        border: none;
        background: transparent;
        cursor: pointer;
        font-size: 15px;
        line-height: 1;
        color: var(--now-text-secondary, #4b5563);
        padding: 2px 4px;
        border-radius: 6px;
      }

      .scroll-canvas {
        display: flex;
        flex-direction: column;
      }

      .canvas-container {
        flex: 1;
        width: 100%;
        display: flex;
        flex-direction: column;
      }

      .chat-thread-container {
        width: 100%;
      }

      .hero {
        max-width: 768px;
        margin: 8vh auto 32px;
        text-align: center;
      }

      .hero-title {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        font-size: 30px;
        font-weight: 500;
        margin: 0 0 24px 0;
        color: var(--now-text-primary, #111827);
      }

      .prompt-box {
        display: flex;
        flex-direction: column;
        gap: 12px;
        background: #ffffff;
        border-radius: 32px;
        padding: 20px 16px 14px 24px;
        box-shadow:
          0 0 0 8px #f4f3f0,
          0 0 8px 8px rgba(0, 0, 0, 0.05),
          0 20px 25px 3px rgba(0, 0, 0, 0.1);
        text-align: left;
        margin: 8px;
      }

      .prompt-input {
        border: none;
        background: transparent;
        font-size: 16px;
        line-height: 24px;
        outline: none;
        color: var(--now-text-primary, #111827);
        font-family: inherit;
      }

      .prompt-foot {
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-height: 36px;
        font-size: 12px;
        color: var(--now-text-secondary, #4b5563);
      }

      .prompt-foot-left {
        display: inline-flex;
        align-items: center;
        gap: 10px;
      }

      .attach-btn {
        width: 32px;
        height: 32px;
        border: none;
        border-radius: 50%;
        background: transparent;
        color: #4a4e58;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
      }

      .attach-btn:hover {
        background: #f1efeb;
      }

      .attach-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }

      .attach-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 6px 4px 10px;
        border-radius: 10px;
        background: #f1efeb;
        font-size: 12.5px;
      }

      .attach-chip button {
        border: none;
        background: none;
        cursor: pointer;
        font-size: 14px;
        color: #4a4e58;
      }

      .attach-error {
        font-size: 12.5px;
        color: #b42318;
      }

      .attach-size {
        color: #6b7280;
        font-size: 11.5px;
      }

      .prompt-send-btn {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background: #c9f0c1;
        color: #4b5f4b;
        border: none;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
      }

      .chips-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        justify-content: center;
        margin-top: 16px;
      }

      .chip-btn {
        padding: 8px 14px;
        border-radius: 10px;
        border: none;
        background: #ffffff;
        font-size: 13px;
        font-weight: 500;
        color: var(--now-text-primary, #111827);
        cursor: pointer;
      }

      .chip-btn:hover {
        background: #f6f4f0;
      }

      .dock {
        position: sticky;
        bottom: 0;
        width: 100%;
        max-width: 768px;
        margin: auto auto 0;
        padding: 12px 0 8px;
        background: linear-gradient(to bottom, rgba(239, 236, 231, 0), var(--otto-canvas, #efece7) 28%);
      }

      .chat-thread-container {
        display: flex;
        flex-direction: column;
        gap: 22px;
        max-width: 720px;
        margin: 8px auto 16px;
      }

      .message-bubble {
        font-size: 13.5px;
        line-height: 1.55;
      }

      .message-bubble.system {
        align-self: center;
        font-size: 12px;
        color: var(--now-text-secondary, #4b5563);
      }

      .agent-head {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 6px;
      }

      .agent-head .when {
        font-weight: 500;
        color: var(--now-text-secondary, #6b7280);
      }

      details.steps {
        margin: 0 0 8px 0;
        font-size: 12.5px;
        color: var(--now-text-secondary, #4b5563);
      }

      details.steps summary {
        cursor: pointer;
        list-style: none;
        font-weight: 500;
      }

      details.steps ul {
        list-style: none;
        margin: 6px 0 0 6px;
        padding: 0 0 0 14px;
        border-left: 1px solid rgba(0, 0, 0, 0.12);
      }

      details.steps li {
        padding: 2px 0;
      }

      details.steps li.failed {
        color: #b91c1c;
      }

      .avatar {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background: #c9f0c1;
        color: #1b4d1b;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        font-weight: 700;
        flex: none;
      }

      .outcome-card {
        display: flex;
        gap: 12px;
        align-items: flex-start;
        padding: 14px 16px;
        border-radius: 16px;
        border: 1px solid var(--now-border-subtle, #e5e7eb);
        background: var(--now-bg-surface-0, #ffffff);
      }

      .outcome-card .mark {
        width: 22px;
        height: 22px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        font-weight: 800;
        color: #ffffff;
        background: #16a34a;
        flex: none;
      }

      .outcome-card.cancelled .mark {
        background: #6b7280;
      }

      .outcome-card .outcome-title {
        font-weight: 700;
        font-size: 13px;
      }

      .outcome-card .outcome-body {
        font-size: 12.5px;
        color: var(--now-text-secondary, #4b5563);
      }

      .ai-footnote {
        margin-top: 10px;
        font-size: 11px;
        color: var(--now-text-secondary, #6b7280);
        text-align: center;
      }

      .tiles-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 16px;
        margin-top: 16px;
      }

      .dashboard-cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 16px;
      }

      .dash-card {
        background: var(--now-bg-surface-0, #ffffff);
        border: 1px solid var(--now-border-subtle, #e5e7eb);
        border-radius: 8px;
        padding: 20px;
      }

      .dash-metric {
        font-size: 28px;
        font-weight: 800;
        margin: 8px 0;
        color: var(--now-text-primary, #111827);
      }
`;
